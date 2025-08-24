import sys, struct, zlib, os, glob

INPUT_ROOT = os.path.join(os.path.dirname(__file__), "input")
OUTPUT_ROOT = os.path.join(os.path.dirname(__file__), "output")

def unpack_toc(path, out_path=None):
    with open(path, "rb") as f:
        data = f.read()
    sig = b"__ZN"
    idx = data.find(sig)
    if idx == -1:
        print("no __ZN signature in", path)
        return
    unc_size = struct.unpack("<I", data[idx+4:idx+8])[0]
    comp_data = data[idx+8:]
    try:
        raw = zlib.decompress(comp_data, -15, unc_size)
    except:
        raw = zlib.decompress(comp_data)
    if not out_path:
        base = os.path.basename(path)
        if "._" in base:
            base = base.rsplit("._",1)[0] + ".toc"
        else:
            base = base + ".toc"
        out_path = os.path.join(OUTPUT_ROOT, base)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as o:
        o.write(raw)
    print(f"decompressed -> {out_path} ({len(raw)} bytes)")

def main():
    os.makedirs(OUTPUT_ROOT, exist_ok=True)
    files = glob.glob(os.path.join(INPUT_ROOT, "*"))
    for p in files:
        if os.path.isfile(p):
            unpack_toc(p)

if __name__ == "__main__":
    main()
