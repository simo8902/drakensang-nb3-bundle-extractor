import sys

def load_map(path):
    d = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or "|" not in line:
                continue
            p, t, h = line.split("|")
            d[p] = h
    return d

def diff(old, new, out_path):
    old_map = load_map(old)
    new_map = load_map(new)

    added = [(p, new_map[p]) for p in new_map if p not in old_map]
    removed = [(p, old_map[p]) for p in old_map if p not in new_map]
    changed = [(p, old_map[p], new_map[p]) for p in new_map if p in old_map and new_map[p] != old_map[p]]

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"ADDED ({len(added)}):\n")
        for p, nh in added:
            f.write(f"{p} | {nh}\n")
        f.write(f"\nREMOVED ({len(removed)}):\n")
        for p, oh in removed:
            f.write(f"{p} | {oh}\n")
        f.write(f"\nCHANGED ({len(changed)}):\n")
        for p, oh, nh in changed:
            f.write(f"{p} | {oh} -> {nh}\n")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("usage: diff.py old.txt new.txt out.txt")
        sys.exit(1)
    diff(sys.argv[1], sys.argv[2], sys.argv[3])
