import sys
import struct

def read_u32(f):
    return struct.unpack("<I", f.read(4))[0]

def read_chunk(f):
    fourcc = f.read(4)
    if not fourcc:
        return None, None, None
    size = read_u32(f)
    data_pos = f.tell()
    return fourcc, size, data_pos

def parse_bank(path):
    with open(path, "rb") as f:
        riff = f.read(4)
        if riff != b"RIFF":
            print("Not RIFF/FMOD bank:", path)
            return
        f.read(4)  # total size
        fcc = f.read(4)
        if fcc.strip() not in [b"FEV", b"FSB", b"FMOD"]:
            print("Not FMOD bank:", fcc)
            return
        print("Parsing FMOD bank:", path)

        while True:
            chunk = read_chunk(f)
            if not chunk[0]:
                break
            fourcc, size, pos = chunk
            f.seek(pos)

            if fourcc == b"LIST":
                subtype = f.read(4)
                print("LIST subtype:", subtype)

            elif fourcc == b"IBSS":
                print("Found IBSS (sample bank reference)")
                data = f.read(size)
                print("IBSS size:", len(data))

            elif fourcc == b"PRJB":  # sometimes "PROJBANK" section
                print("Project/Bank metadata")

            elif fourcc == b"STRG":
                print("Found string table")
                data = f.read(size)
                try:
                    txt = data.decode("utf-8", errors="ignore")
                    print(txt[:200])
                except:
                    pass

            else:
                f.seek(size, 1)

            # align to 2 bytes
            if size % 2 == 1:
                f.seek(1, 1)

if __name__ == "__main__":
    for p in sys.argv[1:]:
        parse_bank(p)
