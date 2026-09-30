# Version Control Client (mygit)

This is a rudimentary version control system client written in Python that mimics basic `git` functionalities. It stores objects as compressed snapshots and tracks branches, commits, and a staging area.

## Features Implemented
- `init`: Initializes an empty repository by creating a `.mygit` directory to store metadata.
- `add`: Computes hashes of file contents, adds them to the `.mygit/objects` database as a blob, and updates the `.mygit/index` staging area.
- `commit`: Creates a tree object based on the staging area, and a commit object referencing that tree and the parent commit.
- `log`: Loops through parent commits and prints history.
- `status`: Compares working directory files with the staging area (index) and the last commit (HEAD) to show untracked, modified, and staged files.
- `branch`: Creates a new branch or lists existing branches.
- `checkout`: Switches to an existing branch by updating the HEAD reference and working directory files.

## How to Run
Prerequisites: Python 3.x installed on your machine.

1. **Initialize the repository**
   ```bash
   python mygit.py init
   ```
2. **Add files to the staging area**
   ```bash
   python mygit.py add <file1> <file2>
   ```
3. **Commit the changes**
   ```bash
   python mygit.py commit -m "Your commit message"
   ```
4. **View the log**
   ```bash
   python mygit.py log
   ```
5. **Check status**
   ```bash
   python mygit.py status
   ```
6. **Create a branch**
   ```bash
   python mygit.py branch <branch_name>
   ```
7. **Switch branches**
   ```bash
   python mygit.py checkout <branch_name>
   ```

## Design Notes
- The objects (commits, trees, blobs) are stored in `.mygit/objects/` under directories named with the first 2 characters of their SHA-1 hash, mimicking standard git.
- The index (staging area) is stored as a simple JSON file in `.mygit/index` mapping paths to SHA-1 hashes.
- Branches are stored in `.mygit/refs/heads/` as text files containing a commit SHA-1.
- `HEAD` tracks the currently checked-out branch using the `ref: refs/heads/<branch>` syntax.
