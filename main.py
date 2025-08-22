import os, sys, struct, zlib

def extract_bundle(path, out_root):
    with open(path, "rb") as f:
        magic = f.read(8)
        if magic != b"_B3NHB3N":
            print("invalid bundle", path)
            return

        files = struct.unpack("<I", f.read(4))[0]
        f.read(4)
        info_off = struct.unpack("<I", f.read(4))[0]
        base_off = struct.unpack("<I", f.read(4))[0]

        names = []
        for _ in range(files):
            sz_bytes = f.read(2)
            if not sz_bytes:
                break
            name_len = struct.unpack("<H", sz_bytes)[0]
            name = f.read(name_len).decode("utf-8")
            names.append(name)

        already = 0
        for name in names:
            out_name = name
            if os.path.exists(out_name) or os.path.exists(out_name.replace(".nz", "")):
                already += 1
                f.read(4); f.read(32); f.read(4); f.read(4)
                continue
            
            dummy2 = f.read(4)
            if not dummy2:
                break
            f.read(32)
            size = struct.unpack("<I", f.read(4))[0]
            offset = struct.unpack("<I", f.read(4))[0] + base_off

            cur = f.tell()
            f.seek(offset)
            sign = f.read(4)

            out_name = name
            os.makedirs(os.path.dirname(out_name), exist_ok=True) if os.path.dirname(out_name) else None

            if sign == b"__ZN":
                xsize = struct.unpack("<I", f.read(4))[0]
                comp_size = size - 8
                comp_data = f.read(comp_size)
                raw = None
                try:
                    raw = zlib.decompress(comp_data, -15, xsize)
                    print(f"[zlib-raw] {out_name} -> {len(raw)}")
                except:
                    try:
                        raw = zlib.decompress(comp_data)
                        print(f"[zlib] {out_name} -> {len(raw)}")
                    except Exception as e:
                        print(f"[fail decompress] {out_name} {e}, dumping raw {len(comp_data)}")
                        raw = comp_data
                with open(out_name.replace(".nz", ""), "wb") as out:
                    out.write(raw)
            else:
                f.seek(offset)
                data = f.read(size)
                with open(out_name, "wb") as out:
                    out.write(data)
                print("Extracted", out_name, size)

            f.seek(cur)
            
        if already == files:
            print(f">>> files already extracted, skipping {os.path.basename(path)}")
        else:
            print(f">>> Done {os.path.basename(path)}")

if __name__ == "__main__":
    for path in sys.argv[1:]:
        print("\033[92m>>> Extracting\033[0m", path)
        extract_bundle(path, "")
        print("\033[92m>>> Done\033[0m", path)