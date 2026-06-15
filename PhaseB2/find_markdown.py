import os

def main():
    root_dir = "d:\\Swarm\\BTP"
    md_files = []
    for root, dirs, files in os.walk(root_dir):
        # Skip directories like checkpoints or cache
        if any(d in root for d in [".claude", "__pycache__", "checkpoints", "logs"]):
            continue
        for file in files:
            if file.endswith(".md"):
                md_files.append(os.path.join(root, file))
                
    with open("found_md.txt", "w") as f:
        for md in md_files:
            f.write(md + "\n")
    print(f"Found {len(md_files)} markdown files.")

if __name__ == "__main__":
    main()
