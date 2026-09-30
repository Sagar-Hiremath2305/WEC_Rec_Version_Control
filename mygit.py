import sys
import os
import hashlib
import zlib
import json
import time

MYGIT_DIR = ".mygit"

def init():
    if os.path.exists(MYGIT_DIR):
        print("Repository already initialized.")
        return
    
    os.makedirs(os.path.join(MYGIT_DIR, "objects"))
    os.makedirs(os.path.join(MYGIT_DIR, "refs", "heads"))
    
    # Initialize index
    with open(os.path.join(MYGIT_DIR, "index"), "w") as f:
        json.dump({}, f)
        
    # Initialize HEAD
    with open(os.path.join(MYGIT_DIR, "HEAD"), "w") as f:
        f.write("ref: refs/heads/master")
        
    print(f"Initialized empty mygit repository in {os.path.abspath(MYGIT_DIR)}")

def hash_object(data, obj_type="blob", write=True):
    header = f"{obj_type} {len(data)}\0".encode()
    if isinstance(data, str):
        data = data.encode()
    store = header + data
    sha = hashlib.sha1(store).hexdigest()
    
    if write:
        obj_dir = os.path.join(MYGIT_DIR, "objects", sha[:2])
        os.makedirs(obj_dir, exist_ok=True)
        obj_path = os.path.join(obj_dir, sha[2:])
        if not os.path.exists(obj_path):
            with open(obj_path, "wb") as f:
                f.write(zlib.compress(store))
                
    return sha

def read_object(sha):
    obj_path = os.path.join(MYGIT_DIR, "objects", sha[:2], sha[2:])
    if not os.path.exists(obj_path):
        return None, None
        
    with open(obj_path, "rb") as f:
        raw = zlib.decompress(f.read())
        
    x = raw.find(b'\0')
    header = raw[:x].decode()
    obj_type, size = header.split(" ")
    data = raw[x+1:]
    
    return obj_type, data

def add(files):
    if not os.path.exists(MYGIT_DIR):
        print("Not a mygit repository.")
        return
        
    index_path = os.path.join(MYGIT_DIR, "index")
    with open(index_path, "r") as f:
        index = json.load(f)
        
    for file in files:
        if not os.path.exists(file):
            print(f"fatal: pathspec '{file}' did not match any files")
            continue
            
        with open(file, "rb") as f:
            data = f.read()
            
        sha = hash_object(data, "blob", write=True)
        # Store relative path
        rel_path = os.path.relpath(file)
        index[rel_path] = sha
        
    with open(index_path, "w") as f:
        json.dump(index, f)
        
    print(f"Added {len(files)} files to staging area.")

def get_head_ref():
    with open(os.path.join(MYGIT_DIR, "HEAD"), "r") as f:
        data = f.read().strip()
    if data.startswith("ref: "):
        return data[5:]
    return None

def get_head_commit():
    ref = get_head_ref()
    if ref:
        ref_path = os.path.join(MYGIT_DIR, ref)
        if os.path.exists(ref_path):
            with open(ref_path, "r") as f:
                return f.read().strip()
    else:
        with open(os.path.join(MYGIT_DIR, "HEAD"), "r") as f:
            return f.read().strip()
    return None

def write_tree(index):
    # For simplicity, flat tree
    # format: list of dicts {type, sha, path}
    tree_entries = []
    for path, sha in index.items():
        tree_entries.append({"type": "blob", "sha": sha, "path": path})
        
    tree_data = json.dumps(tree_entries).encode()
    return hash_object(tree_data, "tree", write=True)

def commit(message):
    if not os.path.exists(MYGIT_DIR):
        print("Not a mygit repository.")
        return
        
    index_path = os.path.join(MYGIT_DIR, "index")
    with open(index_path, "r") as f:
        index = json.load(f)
        
    if not index:
        print("Nothing to commit.")
        return
        
    tree_sha = write_tree(index)
    parent_sha = get_head_commit()
    
    commit_data = {
        "tree": tree_sha,
        "parent": parent_sha,
        "message": message,
        "timestamp": time.time()
    }
    
    commit_sha = hash_object(json.dumps(commit_data).encode(), "commit", write=True)
    
    # Update ref
    ref = get_head_ref()
    if ref:
        ref_path = os.path.join(MYGIT_DIR, ref)
        os.makedirs(os.path.dirname(ref_path), exist_ok=True)
        with open(ref_path, "w") as f:
            f.write(commit_sha)
    else:
        with open(os.path.join(MYGIT_DIR, "HEAD"), "w") as f:
            f.write(commit_sha)
            
    print(f"[{commit_sha[:7]}] {message}")

def log():
    if not os.path.exists(MYGIT_DIR):
        print("Not a mygit repository.")
        return
        
    commit_sha = get_head_commit()
    if not commit_sha:
        print("No commits yet.")
        return
        
    while commit_sha:
        obj_type, data = read_object(commit_sha)
        if obj_type != "commit":
            print(f"Error: {commit_sha} is not a commit")
            break
            
        commit_data = json.loads(data.decode())
        print(f"commit {commit_sha}")
        print(f"Date:  {time.ctime(commit_data['timestamp'])}")
        print(f"\n    {commit_data['message']}\n")
        
        commit_sha = commit_data.get("parent")

def status():
    if not os.path.exists(MYGIT_DIR):
        print("Not a mygit repository.")
        return
        
    index_path = os.path.join(MYGIT_DIR, "index")
    with open(index_path, "r") as f:
        index = json.load(f)
        
    head_commit = get_head_commit()
    head_tree = {}
    if head_commit:
        _, data = read_object(head_commit)
        commit_data = json.loads(data.decode())
        _, tree_data = read_object(commit_data["tree"])
        tree_entries = json.loads(tree_data.decode())
        head_tree = {e["path"]: e["sha"] for e in tree_entries}
        
    head_ref = get_head_ref()
    print("On branch", head_ref.split("/")[-1] if head_ref else "detached HEAD")
    
    # files in index but different from head (staged)
    staged = []
    for path, sha in index.items():
        if path not in head_tree or head_tree[path] != sha:
            staged.append(path)
            
    # files in head but not in index (deleted in index)
    deleted_staged = []
    for path in head_tree:
        if path not in index:
            deleted_staged.append(path)
            
    # modified in working dir (not staged)
    modified = []
    # untracked
    untracked = []
    
    for root, dirs, files in os.walk("."):
        if MYGIT_DIR in root:
            continue
        for file in files:
            path = os.path.relpath(os.path.join(root, file))
            if path.startswith(MYGIT_DIR):
                continue
                
            with open(path, "rb") as f:
                data = f.read()
            sha = hash_object(data, "blob", write=False)
            
            if path in index:
                if index[path] != sha:
                    modified.append(path)
            else:
                untracked.append(path)
                
    if staged or deleted_staged:
        print("\nChanges to be committed:")
        for p in staged:
            print(f"\tmodified/new:   {p}")
        for p in deleted_staged:
            print(f"\tdeleted:        {p}")
            
    if modified:
        print("\nChanges not staged for commit:")
        for p in modified:
            print(f"\tmodified:       {p}")
            
    if untracked:
        print("\nUntracked files:")
        for p in untracked:
            print(f"\t{p}")

def branch(name=None):
    if not os.path.exists(MYGIT_DIR):
        print("Not a mygit repository.")
        return
        
    if name is None:
        # list branches
        head_ref = get_head_ref()
        heads_dir = os.path.join(MYGIT_DIR, "refs", "heads")
        
        # If directory doesn't exist or is empty
        if not os.path.exists(heads_dir) or not os.listdir(heads_dir):
            if head_ref:
                print(f"* {head_ref.split('/')[-1]}")
            return
            
        for f in os.listdir(heads_dir):
            prefix = "* " if head_ref == f"refs/heads/{f}" else "  "
            print(prefix + f)
    else:
        # create branch
        commit_sha = get_head_commit()
        if not commit_sha:
            print("fatal: Not a valid object name: 'master'.")
            return
            
        ref_path = os.path.join(MYGIT_DIR, "refs", "heads", name)
        if os.path.exists(ref_path):
            print(f"fatal: A branch named '{name}' already exists.")
            return
            
        with open(ref_path, "w") as f:
            f.write(commit_sha)
        print(f"Created branch '{name}'")

def checkout(name):
    if not os.path.exists(MYGIT_DIR):
        print("Not a mygit repository.")
        return
        
    ref_path = os.path.join(MYGIT_DIR, "refs", "heads", name)
    if not os.path.exists(ref_path):
        print(f"error: pathspec '{name}' did not match any file(s) known to mygit")
        return
        
    with open(ref_path, "r") as f:
        target_commit_sha = f.read().strip()
        
    # Update HEAD
    with open(os.path.join(MYGIT_DIR, "HEAD"), "w") as f:
        f.write(f"ref: refs/heads/{name}")
        
    # Update working dir
    _, data = read_object(target_commit_sha)
    commit_data = json.loads(data.decode())
    _, tree_data = read_object(commit_data["tree"])
    tree_entries = json.loads(tree_data.decode())
    
    # Update index
    index = {}
    for entry in tree_entries:
        index[entry["path"]] = entry["sha"]
        
        # Write file to working dir
        _, blob_data = read_object(entry["sha"])
        if os.path.dirname(entry["path"]):
            os.makedirs(os.path.dirname(entry["path"]), exist_ok=True)
        with open(entry["path"], "wb") as f:
            f.write(blob_data)
            
    with open(os.path.join(MYGIT_DIR, "index"), "w") as f:
        json.dump(index, f)
        
    print(f"Switched to branch '{name}'")

def main():
    if len(sys.argv) < 2:
        print("Usage: mygit <command> [<args>]")
        print("\nAvailable commands:")
        print("  init                Initialize an empty repository")
        print("  add <file>...       Add file contents to the index")
        print("  commit -m <msg>     Record changes to the repository")
        print("  log                 Show commit logs")
        print("  status              Show the working tree status")
        print("  branch [<name>]     List, create, or delete branches")
        print("  checkout <branch>   Switch branches")
        return
        
    command = sys.argv[1]
    
    if command == "init":
        init()
    elif command == "add":
        add(sys.argv[2:])
    elif command == "commit":
        if len(sys.argv) < 4 or sys.argv[2] != "-m":
            print("Usage: mygit commit -m <message>")
            return
        commit(sys.argv[3])
    elif command == "log":
        log()
    elif command == "status":
        status()
    elif command == "branch":
        if len(sys.argv) > 2:
            branch(sys.argv[2])
        else:
            branch()
    elif command == "checkout":
        if len(sys.argv) < 3:
            print("Usage: mygit checkout <branch>")
            return
        checkout(sys.argv[2])
    else:
        print(f"mygit: '{command}' is not a mygit command.")

if __name__ == "__main__":
    main()
