# PROD. BY SIMO
## UPDATED 08/24/2025

import os, sys, struct, zlib, glob

INPUT_ROOT = os.path.join(os.path.dirname(__file__), "input")
OUTPUT_ROOT = os.path.join(os.path.dirname(__file__), "output")

def _decomp(comp_data: bytes, xsize: int) -> bytes:
    for wb in (15, -15, 31):
        try:
            return zlib.decompress(comp_data, wb, xsize)
        except Exception:
            pass
    d = zlib.decompressobj()
    return d.decompress(comp_data, xsize if xsize else 0) + d.flush()

def _write_out(rel_path: str, data: bytes):
    out_path = os.path.join(OUTPUT_ROOT, rel_path)
    d = os.path.dirname(out_path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(out_path, "wb") as out:
        out.write(data)
    return out_path

def extract_single(path: str):
    with open(path, "rb") as f:
        sig = f.read(4)
        if sig != b"__ZN":
            return False
        xsize = struct.unpack("<I", f.read(4))[0]
        comp = f.read()
        raw = _decomp(comp, xsize)
        base = os.path.splitext(os.path.basename(path))[0]
        out_rel = base
        p = _write_out(out_rel, raw)
        print(f"[single] {path} -> {p} ({len(raw)})")
        return True

def extract_bundle(path: str):
    with open(path, "rb") as f:
        magic = f.read(8)
        if magic not in (b"_B3NHB3N", b"_NZ2", b"_2ZN"):
            print("invalid bundle", path)
            return
        files = struct.unpack("<I", f.read(4))[0]
        f.read(4)
        info_off = struct.unpack("<I", f.read(4))[0]
        base_off = struct.unpack("<I", f.read(4))[0]

        names = []
        for _ in range(files):
            if magic == b"_B3NHB3N":
                sz = f.read(2)
                if not sz:
                    break
                nlen = struct.unpack("<H", sz)[0]
                name = f.read(nlen).decode("utf-8")
                names.append(name)
            else:
                chars = []
                while True:
                    c = f.read(1)
                    if not c or c == b"\x00":
                        break
                    chars.append(c)
                if not chars:
                    break
                name = b"".join(chars).decode("utf-8")
                names.append(name)

        for name in names:
            hdr = f.read(4)
            if not hdr:
                break
            f.read(32)
            size = struct.unpack("<I", f.read(4))[0]
            offset = struct.unpack("<I", f.read(4))[0] + base_off

            cur = f.tell()
            f.seek(offset)
            sign = f.read(4)

            if sign == b"__ZN":
                xsize = struct.unpack("<I", f.read(4))[0]
                comp = f.read(size - 8)
                try:
                    raw = _decomp(comp, xsize)
                    out_rel = name.replace(".nz", "")
                    p = _write_out(out_rel, raw)
                    print(f"[ZLIB] {p} ({len(raw)})")
                except Exception as e:
                    out_rel = name.replace(".nz", "")
                    p = _write_out(out_rel, comp)
                    print(f"\033[91m[RAW]\033[0m {p} ({len(comp)}) {e}")
            else:
                f.seek(offset)
                data = f.read(size)
                out_rel = name
                p = _write_out(out_rel, data)
                print(f"[copy] {p} ({size})")

            f.seek(cur)

        print(f">>> Done {os.path.basename(path)}")

def process_path(p: str):
    if os.path.isdir(p):
        for fp in glob.glob(os.path.join(p, "**", "*.nb._*"), recursive=True):
            process_path(fp)
        return
    try:
        if extract_single(p):
            return
        extract_bundle(p)
    except Exception as e:
        print(f"[fail] {p} {e}")

def main():
    os.makedirs(OUTPUT_ROOT, exist_ok=True)
    args = sys.argv[1:]
    if not args or "all" in args:
        for path in glob.glob(os.path.join(INPUT_ROOT, "**", "*.nb._*"), recursive=True):
            print("\033[92m>>> Extracting\033[0m", path)
            process_path(path)
            print("\033[92m>>> Done\033[0m", path)
        return
    for p in args:
        print("\033[92m>>> Extracting\033[0m", p)
        process_path(p)
        print("\033[92m>>> Done\033[0m", p)

if __name__ == "__main__":
    main()