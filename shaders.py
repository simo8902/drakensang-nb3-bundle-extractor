import struct, argparse, os, json, hashlib, re

def u16(data, off): return struct.unpack_from("<H", data, off)[0]
def u32(data, off): return struct.unpack_from("<I", data, off)[0]

def is_printable(bs): return all(32 <= b < 127 for b in bs)

def read_u16_name(data, off):
    if off+2 > len(data): return None
    n = u16(data, off)
    if n == 0 or n > 64: return None
    end = off+2+n
    if end > len(data): return None
    s = data[off+2:end]
    if not is_printable(s): return None
    return n, s.decode("ascii")

def scan_top_entries(data, start=12, max_hint=None):
    entries = []
    off = start
    while off < len(data)-16:
        cand = read_u16_name(data, off)
        if cand:
            n, name = cand
            a = u32(data, off+2+n)
            marker = u32(data, off+2+n+4)
            b = u32(data, off+2+n+8)
            if marker == 0xFEFF0901:
                entries.append({"name": name, "off": off, "a": a, "b": b})
                off = off + 2 + n + 12
                if max_hint and len(entries) >= max_hint:
                    break
                continue
        off += 1
    return entries

def find_sentinels(data, start, end):
    sent = b"\xFF\xFF\x00\x00"
    out = []
    i = start
    while True:
        i = data.find(sent, i, end)
        if i == -1: break
        if i+16 <= end:
            if data[i+8:i+12] == b"\x00\x00\x00\x00" and data[i+12:i+16] == b"\xFF\xFF\xFF\xFF":
                out.append(i)
        i += 1
    return out

def scan_tags(data, start, end):
    tags = []
    i = start
    while i+8 <= end:
        if data[i] == 0xFE and data[i+1] == 0xFF:
            size = u16(data, i+2)
            tag = data[i+4:i+8]
            if is_printable(tag):
                tags.append((i, size, tag.decode("ascii")))
                i += 8
                continue
        i += 1
    return tags

def extract_ctab_names(data, start, end):
    names = []
    i = start
    while i < end-4:
        if 32 <= data[i] < 127:
            j = i
            while j < end and 32 <= data[j] < 127:
                j += 1
            if j < end and data[j] == 0x00 and j+2 < end and data[j+1] == 0xAB:
                s = data[i:j].decode("ascii")
                if "HLSL Shader Compiler" not in s:
                    names.append(s)
                i = j+1
                continue
        i += 1
    return names

def scan_profiles(data, start, end):
    profs = []
    for key in (b"vs_3_0\x00", b"ps_3_0\x00"):
        i = start
        while True:
            i = data.find(key, i, end)
            if i == -1: break
            profs.append(key.decode("ascii").strip("\x00"))
            i += 1
    return profs

def classify_blob(blob):
    profs = blob["profiles"]
    tags = len(blob["tags"])
    names = blob["ctab_names"]
    if "vs_3_0" in profs: return "VS"
    if "ps_3_0" in profs: return "PS"
    if tags == 3 and "CullMode" in names: return "STATE"
    return "OTHER"

def group_blobs(blobs):
    groups = []
    i = 0
    while i < len(blobs):
        g = {"VS": None, "PS": None, "STATE": None, "OTHER": []}
        g["start"] = blobs[i]["start"]

        if blobs[i]["type"] == "VS":
            g["VS"] = blobs[i]; i += 1
            if i < len(blobs) and blobs[i]["type"] == "PS":
                g["PS"] = blobs[i]; i += 1
            if i < len(blobs) and blobs[i]["type"] == "STATE":
                g["STATE"] = blobs[i]; i += 1
        elif blobs[i]["type"] == "PS":
            g["PS"] = blobs[i]; i += 1
            if i < len(blobs) and blobs[i]["type"] == "STATE":
                g["STATE"] = blobs[i]; i += 1
        elif blobs[i]["type"] == "STATE":
            g["STATE"] = blobs[i]; i += 1
        else:
            g["OTHER"].append(blobs[i]); i += 1

        g["end"] = blobs[i-1]["end"]
        groups.append(g)
    return groups

def sanitize(name):
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)

def carve_fxlc_code(blob, tags):
    # pick the LAST FXLC tag in this blob
    fxlc_tags = [t for t in tags if t[2] == "FXLC"]
    if not fxlc_tags:
        return None, None
    toff, size, _ = fxlc_tags[-1]

    code_start = toff + 8  # FE FF + size + "FXLC"
    if code_start >= len(blob):
        return None, None

    if 0 < size <= (len(blob) - code_start):
        code_end = code_start + size
    else:
        code_end = len(blob)

    return code_start, code_end
    
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("outdir")
    ap.add_argument("--dedup", action="store_true")
    ap.add_argument("--require-vs-ps", action="store_true")
    args = ap.parse_args()

    data = open(args.file, "rb").read()
    if data[:4] != b"PDHS":
        raise ValueError("Bad magic")

    hint = u32(data, 8)
    entries = scan_top_entries(data, 12, max_hint=hint if hint < 0x1000 else None)
    for i, e in enumerate(entries):
        e["end"] = entries[i+1]["off"] if i+1 < len(entries) else len(data)

    os.makedirs(args.outdir, exist_ok=True)
    manifest = []

    seen = set()

    for e in entries:
        start, end = e["off"], e["end"]
        sents = find_sentinels(data, start, end)

        blobs = []
        for si, s in enumerate(sents):
            bstart = s + 16
            bend = sents[si+1] if si+1 < len(sents) else end
            tags = scan_tags(data, bstart, bend)

            ctab_names = []
            for toff, size, tag in tags:
                if tag == "CTAB":
                    region_start = toff + 8
                    region_end = min(bend, region_start + size + 0x2000)
                    ctab_names += extract_ctab_names(data, region_start, region_end)

            blob = {
                "start": bstart, "end": bend,
                "profiles": scan_profiles(data, bstart, bend),
                "tags": tags,
                "ctab_names": ctab_names
            }
            blob["type"] = classify_blob(blob)
            blobs.append(blob)

        groups = group_blobs(blobs)

        entry_dir = os.path.join(args.outdir, sanitize(e["name"]))
        os.makedirs(entry_dir, exist_ok=True)

        for gi, g in enumerate(groups):
            if args.require_vs_ps and not (g["VS"] and g["PS"]):
                continue

            group_id = f"{sanitize(e['name'])}_g{gi:03d}"
            group_info = {"entry": e["name"], "group": gi, "files": {}}

            for key in ("VS", "PS", "STATE"):
                blob = g[key]
                if not blob: 
                    continue
                raw = data[blob["start"]:blob["end"]]
                h = hashlib.sha1(raw).hexdigest()

                if args.dedup and h in seen:
                    continue
                seen.add(h)

                fname = f"{group_id}_{key}_{h[:8]}.bin"
                fpath = os.path.join(entry_dir, fname)
                with open(fpath, "wb") as f:
                    f.write(raw)
                    
                code_start, code_end = carve_fxlc_code(raw, blob["tags"])
                if code_start is not None:
                    code = raw[code_start:code_end]
                    code_name = f"{group_id}_{key}_{h[:8]}.fxlc.bin"
                    code_path = os.path.join(entry_dir, code_name)
                    with open(code_path, "wb") as cf:
                        cf.write(code)

                    group_info["files"][key]["fxlc"] = {
                        "file": code_name,
                        "start_in_blob": code_start,
                        "end_in_blob": code_end
                    }
                group_info["files"][key] = {
                    "file": fname,
                    "start": blob["start"],
                    "end": blob["end"],
                    "sha1": h
                }

            manifest.append(group_info)

    with open(os.path.join(args.outdir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    print("done")

if __name__ == "__main__":
    main()