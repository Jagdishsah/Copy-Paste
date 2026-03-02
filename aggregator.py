import os

# --- CONFIGURATION ---
OUTPUT_FILE = "Code_Master.txt"
EXCLUDE_DIRS = {'.git', '__pycache__', 'venv', '.streamlit', 'Data'} 
EXCLUDE_FILES = {'secrets.toml', OUTPUT_FILE, 'aggregator.py'}
INCLUDE_EXTENSIONS = {'.py', '.md', '.txt', '.toml', '.yaml'}

def generate_tree(startpath):
    tree = ["PROJECT TREE", "============"]
    for root, dirs, files in os.walk(startpath):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * (level)
        tree.append(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            if any(f.endswith(ext) for ext in INCLUDE_EXTENSIONS) and f not in EXCLUDE_FILES:
                tree.append(f"{subindent}{f}")
    return "\n".join(tree)

def aggregate_code(startpath):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        # 1. Write the Tree Structure
        out.write(generate_tree(startpath))
        out.write("\n\n" + "="*80 + "\n")
        out.write("FILE CONTENTS\n")
        out.write("="*80 + "\n\n")

        # 2. Iterate and write file contents
        for root, dirs, files in os.walk(startpath):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for file in sorted(files):
                if any(file.endswith(ext) for ext in INCLUDE_EXTENSIONS) and file not in EXCLUDE_FILES:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, startpath)
                    
                    print(f"Adding: {rel_path}")
                    out.write(f"PROGRAM: {rel_path}\n")
                    out.write("-" * 80 + "\n")
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            out.write(f.read())
                    except Exception as e:
                        out.write(f"ERROR READING FILE: {e}")
                    out.write("\n\n")

if __name__ == "__main__":
    print(f"🚀 Generating {OUTPUT_FILE}...")
    aggregate_code(os.getcwd())
    print(f"✅ Done! Open {OUTPUT_FILE} to see your entire project.")
