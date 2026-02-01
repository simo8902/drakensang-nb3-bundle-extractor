# PROD. BY SIMEON
# UPDATED 02/01/2026

import os, sys, struct, zlib, glob, traceback, time, hashlib, re

INPUT_ROOT = os.path.join(os.path.dirname(__file__), "input")
OUTPUT_ROOT = os.path.join(os.path.dirname(__file__), "output")

ANSI = os.environ.get("NO_COLOR", "") == ""
C_RESET = "\033[0m" if ANSI else ""
C_RED = "\033[91m" if ANSI else ""
C_GRN = "\033[92m" if ANSI else ""
C_YEL = "\033[93m" if ANSI else ""
C_CYN = "\033[96m" if ANSI else ""
VERBOSE = True
DEBUG = True

def _ts():
    return time.strftime("%H:%M:%S")

def _log(prefix, color, msg):
    print(f"{color}[{_ts()}] {prefix} {msg}{C_RESET}", flush=True)

def info(msg): _log("INFO", C_CYN, msg)
def ok(msg): _log("OK", C_GRN, msg)
def warn(msg): _log("WARN", C_YEL, msg)
def err(msg): _log("ERR", C_RED, msg)
def dbg(msg):
    if DEBUG: _log("DBG", C_CYN, msg)

def _hexdump(b, maxlen=64):
    s = b[:maxlen]
    return " ".join(f"{x:02X}" for x in s) + (" ..." if len(b) > maxlen else "")

def _sanitize_rel(rel_path: str) -> str:
    rel_path = rel_path.replace("\\", "/")
    while rel_path.startswith("/"): rel_path = rel_path[1:]
    parts = []
    for p in rel_path.split("/"):
        if p in ("", ".",):
            continue
        if p == "..":
            if parts: parts.pop()
            continue
        parts.append(p)
    return "/".join(parts)

def _decomp(comp_data: bytes, xsize: int) -> bytes:
    for wb in (15, -15, 31):
        try:
            # dbg(f"zlib.decompress wb={wb} xsize={xsize} comp={len(comp_data)}")
            return zlib.decompress(comp_data, wb, xsize)
        except Exception as e:
            dbg(f"zlib fail wb={wb}: {e}")
    d = zlib.decompressobj()
    try:
       # dbg(f"decompressobj xsize={xsize}")
        return d.decompress(comp_data, xsize if xsize else 0) + d.flush()
    except Exception as e:
        raise RuntimeError(f"decompressobj failed: {e}")

def _write_out(rel_path: str, data: bytes):
    rel_path = _sanitize_rel(rel_path)
    out_path = os.path.join(OUTPUT_ROOT, rel_path)
    d = os.path.dirname(out_path)
    try:
        if d: os.makedirs(d, exist_ok=True)
        with open(out_path, "wb") as out:
            out.write(data)
       # ok(f"write -> {out_path} ({len(data)} bytes)")
        return out_path
    except Exception as e:
        err(f"write fail {out_path}: {e}")
        raise

def extract_single(path: str):
   # info(f"[single] open {path}")
    try:
        with open(path, "rb") as f:
            sig = f.read(4)
            if sig != b"__ZN":
               # dbg(f"[single] magic={sig!r}")
                return False
            xsize_b = f.read(4)
            if len(xsize_b) != 4:
                err(f"[single] size field truncated")
                return False
            xsize = struct.unpack("<I", xsize_b)[0]
            comp = f.read()
           # dbg(f"[single] xsize={xsize} comp_len={len(comp)} head={_hexdump(comp)}")
            try:
                raw = _decomp(comp, xsize)
            except Exception as e:
                err(f"[single] decompress fail: {e}")
                traceback.print_exc()
                return False
            base = os.path.basename(path)
            out_rel = base
            p = _write_out(out_rel, raw)
           # ok(f"[single] {path} -> {p}")
            return True
    except Exception as e:
        err(f"[single] {path} error: {e}")
        traceback.print_exc()
        return False

def extract_bundle(path: str):
   # info(f"[bundle] open {path}")
    try:
        with open(path, "rb") as f:
            magic = f.read(8)
            # dbg(f"[bundle] magic={magic!r}")
            if magic not in (b"_B3NHB3N"):
                warn(f"[bundle] invalid magic {magic!r} {path}")
                return False
            files_b = f.read(4)
            if len(files_b) != 4:
                err("[bundle] file count truncated")
                return False
            files = struct.unpack("<I", files_b)[0]
            skip = f.read(4)
            info_off_b = f.read(4)
            base_off_b = f.read(4)
            if len(info_off_b) != 4 or len(base_off_b) != 4:
                err("[bundle] header truncated")
                return False
            info_off = struct.unpack("<I", info_off_b)[0]
            base_off = struct.unpack("<I", base_off_b)[0]
           # dbg(f"[bundle] files={files} info_off=0x{info_off:X} base_off=0x{base_off:X}")
            names = []
            for i in range(files):
                if magic == b"_B3NHB3N":
                    sz = f.read(2)
                    if len(sz) != 2:
                        err(f"[bundle] name len truncated at idx {i}")
                        break
                    nlen = struct.unpack("<H", sz)[0]
                    name_b = f.read(nlen)
                    if len(name_b) != nlen:
                        err(f"[bundle] name truncated at idx {i}")
                        break
                    try:
                        name = name_b.decode("utf-8", errors="replace")
                    except Exception as e:
                        name = f"entry_{i}"
                        warn(f"[bundle] name decode fail idx {i}: {e}")
                    names.append(name)
                else:
                    chars = []
                    while True:
                        c = f.read(1)
                        if not c:
                            err(f"[bundle] unexpected EOF in name idx {i}")
                            break
                        if c == b"\x00":
                            break
                        chars.append(c)
                    if not chars:
                        break
                    name = b"".join(chars).decode("utf-8", errors="replace")
                    names.append(name)
           # info(f"[bundle] names={len(names)}")
            for i, name in enumerate(names):
                hdr = f.read(4)
                if len(hdr) != 4:
                    warn(f"[bundle] entry hdr EOF at {i}")
                    break
                f.read(32)
                sz_b = f.read(4)
                off_b = f.read(4)
                if len(sz_b) != 4 or len(off_b) != 4:
                    err(f"[bundle] entry size/offset truncated at {i}")
                    break
                size = struct.unpack("<I", sz_b)[0]
                offset = struct.unpack("<I", off_b)[0] + base_off
                cur = f.tell()
               # dbg(f"[bundle] idx={i} name={name} size={size} file_off=0x{offset:X}")
                f.seek(offset)
                sign = f.read(4)
                if len(sign) != 4:
                    err(f"[bundle] idx={i} sign truncated")
                    f.seek(cur)
                    continue
                if sign == b"__ZN":
                    xsize_b = f.read(4)
                    if len(xsize_b) != 4:
                        err(f"[bundle] idx={i} xsize truncated")
                        f.seek(cur)
                        continue
                    xsize = struct.unpack("<I", xsize_b)[0]
                    to_read = max(0, size - 8)
                    comp = f.read(to_read)
                    #dbg(f"[bundle] idx={i} zlib xsize={xsize} comp_len={len(comp)}")
                    try:
                        raw = _decomp(comp, xsize)
                        out_rel = name.replace(".nz", "")
                        _write_out(out_rel, raw)
                        #ok(f"[bundle] zlib -> {out_rel} ({len(raw)})")
                    except Exception as e:
                        warn(f"[bundle] zlib fail idx={i}: {e}; writing raw")
                        out_rel = name.replace(".nz", "")
                        _write_out(out_rel, comp)
                else:
                    f.seek(offset)
                    data = f.read(size)
                   # dbg(f"[bundle] idx={i} copy size={len(data)}")
                    out_rel = name
                    _write_out(out_rel, data)
                f.seek(cur)
           # ok(f"[bundle] done {os.path.basename(path)}")
            return True
    except Exception as e:
        err(f"[bundle] {path} error: {e}")
        traceback.print_exc()
        return False

def extract_ib3n(path: str, rel: str):
    try:
        with open(path, "rb") as f:
            m = f.read(4)
            if m != b"IB3N":
                return False
            cnt = struct.unpack("<H", f.read(2))[0]
            entries = []
            for i in range(cnt):
                nlen = struct.unpack("<H", f.read(2))[0]
                name = f.read(nlen).decode("utf-8", errors="replace")
                size = struct.unpack("<I", f.read(4))[0]
                hlen = struct.unpack("<H", f.read(2))[0]
                h = f.read(hlen).decode("ascii", errors="ignore")
                entries.append((name, size, h))

        rel_clean = _sanitize_rel(rel)
        hname = hashlib.sha1(rel_clean.encode()).hexdigest()[:8]
        base = os.path.splitext(rel_clean)[0].replace("/", "_")
        out_rel = f"_toc/{base}_{hname}.toc.txt"

        data = "\n".join(f"{i}\t{e[0]}\t{e[1]}\t{e[2]}" for i, e in enumerate(entries))
        _write_out(out_rel, data.encode("utf-8"))
        return True
    except Exception as e:
        err(f"[ib3n] {path} error: {e}")
        traceback.print_exc()
        return False
        
def extract_bxml(path: str, rel: str):
    import os, struct

    def u32(b, o): return struct.unpack_from('<I', b, o)[0]
    def u16(b, o): return struct.unpack_from('<H', b, o)[0]

    def parse_lmxb_bounds(data, pos, max_end=None):
        if data[pos:pos+4] != b'LMXB': return None
        off = pos + 4
        if off + 12 > len(data): return None
        na = u32(data, off); off += 4
        nn = u32(data, off); off += 4
        ns = u32(data, off); off += 4
        off += nn * 24 + na * 8
        p = off
        for _ in range(ns):
            q = data.find(b'\x00', p, max_end if max_end else len(data))
            if q < 0: return None
            p = q + 1
        if max_end and p > max_end: return None
        return pos, p

    def sanitize(name):
        return ''.join(c if c.isalnum() or c in ('-','_','.', '/','\\') else '_' for c in name) or 'unnamed'

    try:
        dbg(f"[bxml] scanning {path}")
        with open(path, 'rb') as f:
            data = f.read()

        if data[:4] not in (b'KCAP', b'PBXM'):
            dbg(f"[bxml] skipped (no KCAP/PBXM) {path}")
            return False

        nl = u16(data, 8)
        name = data[10:10+nl].decode('utf-8', 'ignore').strip()
        subdir = os.path.join(OUTPUT_ROOT, sanitize(name))
        os.makedirs(subdir, exist_ok=True)

        pos = 10 + nl + 4
        count = 0
        end_limit = len(data)

        dbg(f"[bxml] begin scan KCAP={name} size={end_limit}")

        while True:
            p = data.find(b'LMXB', pos, end_limit)
            if p == -1:
                break
            a = max(0, p - 4)
            nxt = data.find(b'LMXB', p + 4, end_limit)
            if nxt == -1:
                nxt = end_limit
            q = nxt
            while q > p and data[q-1] == 0:
                q -= 1
            b = q
            chunk = data[p:b]
            tail = data[max(0, a - 512):a]
            parts = tail.split(b'\x00')
            name_bytes = b''
            for s in reversed(parts):
                if b'/' in s and len(s) > 4:
                    name_bytes = s
                    break
            name2 = name_bytes.decode('utf-8', 'ignore').strip() if name_bytes else f'lmxb_{count:02d}'
            outp = os.path.join(subdir, f'{sanitize(name2)}.bxml')
            os.makedirs(os.path.dirname(outp), exist_ok=True)
            with open(outp, 'wb') as o:
                o.write(chunk)
            dbg(f"[bxml] wrote {outp} ({len(chunk)} bytes)")
            count += 1
            pos = nxt

        if count == 0:
            warn(f"[bxml] no LMXB found in {os.path.basename(path)}")
            return False
        ok(f"[bxml] extracted {count} LMXB chunks from {os.path.basename(path)}")
        return True
    except Exception as e:
        err(f"[bxml] {path} error: {e}")
        traceback.print_exc()
        return False



def iter_input_files(root: str):
    for dp, _, fns in os.walk(root):
        for fn in fns:
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, root)
            yield p, rel

def handle_file(path: str, rel: str):
  #  info(f"process file {path}")
    try:
        if extract_single(path):
            return True
        if extract_ib3n(path, rel):
            return True
        if extract_bundle(path):
            # for root, _, files in os.walk(OUTPUT_ROOT):
                #for fn in files:
                    # fp = os.path.join(root, fn)
                    # with open(fp, 'rb') as f:
                       # sig = f.read(4)
                       # if sig in (b'KCAP', b'PBXM'):
                        #    extract_bxml(fp, fn)
            return True
        warn(f"unparsed -> {rel}")
        try:
            with open(path, "rb") as f:
                data = f.read()
            _write_out(rel, data)
            ok(f"raw -> {rel} ({len(data)} bytes)")
        except Exception as e:
            err(f"copy fail {path}: {e}")
        return False
    except Exception as e:
        err(f"handle_file fail {path}: {e}")
        traceback.print_exc()
        return False

def process_path(p: str):
    # info(f"process {p}")
    if os.path.isdir(p):
        count = 0
        for fp, rel in iter_input_files(p):
            handle_file(fp, rel)
            count += 1
       # info(f"processed {count} files in dir {p}")
        return
    rel = os.path.relpath(p, INPUT_ROOT) if os.path.commonpath([INPUT_ROOT, os.path.abspath(p)]) == INPUT_ROOT else os.path.basename(p)
    handle_file(p, rel)

def relocate_by_toc():
    hash_to_path = {}
    toc_files = set()
    for root, _, files in os.walk(OUTPUT_ROOT):
        for fn in files:
            if '__toc' not in fn: continue
            fp = os.path.normpath(os.path.join(root, fn))
            toc_files.add(fp)
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line: continue
                        parts = line.split('|')
                        if len(parts) == 3 and parts[1] == 'f':
                            hash_to_path[parts[2]] = parts[0]
            except Exception as e:
                err(f"[toc] parse {fp}: {e}")
    info(f"[toc] {len(hash_to_path)} entries | {len(toc_files)} toc files")
    moved = skipped = 0
    for root, _, files in os.walk(OUTPUT_ROOT):
        for fn in list(files):
            fp = os.path.normpath(os.path.join(root, fn))
            if fp in toc_files: continue
            m = re.search(r'\._([0-9a-fA-F]{32})$', fn)
            if not m: continue
            h = m.group(1)
            if h in hash_to_path:
                target = os.path.join(OUTPUT_ROOT, hash_to_path[h])
                os.makedirs(os.path.dirname(target), exist_ok=True)
                os.replace(fp, target)
                moved += 1
            else:
                new_fn = re.sub(r'\._[0-9a-fA-F]{32}$', '', fn)
                os.rename(fp, os.path.join(root, new_fn))
                skipped += 1
                warn(f"[toc] no match h={h} fn={fn}")
    ok(f"[toc] moved={moved} stripped={skipped}")
    
def main():
    os.makedirs(OUTPUT_ROOT, exist_ok=True)
    args = sys.argv[1:]
    if not args or "all" in args:
        paths = list(iter_input_files(INPUT_ROOT))
        if not paths:
            warn(f"no input files in {INPUT_ROOT}")
        for path, rel in paths:
            #info(f"{C_GRN}>>> Extracting{C_RESET} {path}")
            handle_file(path, rel)
            #info(f"{C_GRN}>>> Done{C_RESET} {path}")
        relocate_by_toc()
        return
    for p in args:
        #info(f"{C_GRN}>>> Extracting{C_RESET} {p}")
        process_path(p)
        #info(f"{C_GRN}>>> Done{C_RESET} {p}")
    relocate_by_toc()
    
if __name__ == "__main__":
    main()