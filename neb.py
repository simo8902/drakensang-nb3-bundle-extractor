# PROD. BY SIMO
# UPDATED 09/02/2025

import os, sys, struct, zlib, glob, traceback, time, hashlib

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
            if magic not in (b"_B3NHB3N", b"_NZ2", b"_2ZN"):
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
            return True
        warn(f"unparsed -> {rel}")
        try:
            with open(path, "rb") as f:
                data = f.read()
            _write_out(os.path.join("_unparsed", rel), data)
            ok(f"raw copy -> _unparsed/{rel} ({len(data)} bytes)")
        except Exception as e:
            err(f"unparsed copy fail {path}: {e}")
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
        return
    for p in args:
        #info(f"{C_GRN}>>> Extracting{C_RESET} {p}")
        process_path(p)
        #info(f"{C_GRN}>>> Done{C_RESET} {p}")

if __name__ == "__main__":
    main()
