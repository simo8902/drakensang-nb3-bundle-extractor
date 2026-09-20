# PROD. BY SIMEON
# UPDATED 02/01/2026

import os, sys, struct, zlib, glob, traceback, time, hashlib, re, shutil
import lzma

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

BUNDLE_STAGE_ROOT = "__bundle_members"

def _decomp_nz2(encoded: bytes) -> bytes:
    if len(encoded) < 13 or encoded[:4] != b"_2ZN":
        raise ValueError("_2ZN header truncated or invalid")

    props = encoded[4:9]
    prop = props[0]
    if prop >= 9 * 5 * 5:
        raise ValueError(f"invalid LZMA1 properties: 0x{prop:02X}")

    lc = prop % 9
    remainder = prop // 9
    lp = remainder % 5
    pb = remainder // 5
    dict_size = struct.unpack_from("<I", props, 1)[0]
    decoded_size = struct.unpack_from("<I", encoded, 9)[0]

    filters = [{
        "id": lzma.FILTER_LZMA1,
        "dict_size": dict_size,
        "lc": lc,
        "lp": lp,
        "pb": pb,
    }]
    decoder = lzma.LZMADecompressor(
        format=lzma.FORMAT_RAW,
        filters=filters,
    )
    raw = decoder.decompress(encoded[13:], max_length=decoded_size)
    if len(raw) != decoded_size:
        raise ValueError(
            f"_2ZN decoded size mismatch: {len(raw)} != {decoded_size}"
        )
    return raw
    
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
    try:
        raw = zlib.decompress(comp_data, 15)
    except zlib.error as e:
        raise RuntimeError(f"zlib decompress failed: {e}") from e
    if len(raw) != xsize:
        raise ValueError(f"zlib decoded size mismatch: {len(raw)} != {xsize}")
    return raw

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
    try:
        with open(path, "rb") as f:
            sig = f.read(4)
            if sig not in (b"__ZN", b"ZN__", b"_2ZN"):
                return False
            try:
                if sig == b"_2ZN":
                    raw = _decomp_nz2(sig + f.read())
                else:
                    xsize_b = f.read(4)
                    if len(xsize_b) != 4:
                        err(f"[single] size field truncated")
                        return False
                    xsize = struct.unpack("<I", xsize_b)[0]
                    comp = f.read()
                    raw = _decomp(comp, xsize)
            except Exception as e:
                err(f"[single] decompress fail: {e}")
                traceback.print_exc()
                return False
            base = os.path.basename(path)
            out_rel = base
            out_path = _write_out(out_rel, raw)
            if raw[:4] in (b"KCAP", b"PBXM"):
                extract_bxml(out_path, out_rel)
            return True
    except Exception as e:
        err(f"[single] {path} error: {e}")
        traceback.print_exc()
        return False

def extract_bundle(path: str):
    try:
        with open(path, "rb") as f:
            magic = f.read(8)
            if magic != b"_B3NHB3N":
                return False

            files_b = f.read(4)
            if len(files_b) != 4:
                raise ValueError("file count truncated")
            files = struct.unpack("<I", files_b)[0]

            reserved_b = f.read(4)
            info_off_b = f.read(4)
            base_off_b = f.read(4)
            if (
                len(reserved_b) != 4
                or len(info_off_b) != 4
                or len(base_off_b) != 4
            ):
                raise ValueError("header truncated")
            info_off = struct.unpack("<I", info_off_b)[0]
            base_off = struct.unpack("<I", base_off_b)[0]

            names = []
            for i in range(files):
                size_b = f.read(2)
                if len(size_b) != 2:
                    raise ValueError(f"name length truncated at idx {i}")
                name_len = struct.unpack("<H", size_b)[0]
                name_b = f.read(name_len)
                if len(name_b) != name_len:
                    raise ValueError(f"name truncated at idx {i}")
                names.append(name_b.decode("utf-8", errors="replace"))

            if f.tell() != info_off:
                raise ValueError(
                    f"info offset mismatch: {f.tell()} != {info_off}"
                )

            member_count = 0
            for i, name in enumerate(names):
                record_pos = f.tell()
                record = f.read(44)
                if len(record) != 44:
                    raise ValueError(f"entry record truncated at idx {i}")

                record_hash = record[4:36]
                size = struct.unpack_from("<I", record, 36)[0]
                rel_offset = struct.unpack_from("<I", record, 40)[0]
                offset = rel_offset + base_off

                f.seek(offset)
                blob = f.read(size)
                if len(blob) != size:
                    raise ValueError(
                        f"entry data truncated at idx {i}: "
                        f"{len(blob)} != {size}"
                    )
                f.seek(record_pos + 44)

                actual_hash = hashlib.md5(blob).hexdigest().encode("ascii")
                if record_hash.lower() != actual_hash:
                    raise ValueError(
                        f"entry hash mismatch at idx {i}: "
                        f"{record_hash!r} != {actual_hash!r}"
                    )

                out_rel = _sanitize_rel(name)
                if out_rel.lower().endswith(".nz"):
                    out_rel = out_rel[:-3]
                if not out_rel:
                    raise ValueError(f"empty member name at idx {i}")

                if blob[:4] in (b"__ZN", b"ZN__"):
                    if size < 8:
                        raise ValueError(f"compressed entry too small at idx {i}")
                    xsize = struct.unpack_from("<I", blob, 4)[0]
                    raw = _decomp(blob[8:], xsize)
                else:
                    raw = blob

                out_path = _write_out(out_rel, raw)
                member_count += 1

                if raw[:4] in (b"KCAP", b"PBXM"):
                    extract_bxml(out_path, out_rel)

            ok(
                f"[bundle] unpacked {os.path.basename(path)} "
                f"members={member_count}"
            )
            return True
    except Exception as e:
        err(f"[bundle] {path} error: {e}")
        traceback.print_exc()
        return None

def extract_ib3n(path: str, rel: str):
    def read_string(stream):
        length_b = stream.read(2)
        if len(length_b) != 2:
            raise ValueError("string length truncated")
        length = struct.unpack("<H", length_b)[0]
        value = stream.read(length)
        if len(value) != length:
            raise ValueError("string data truncated")
        return value.decode("utf-8", errors="replace")

    try:
        with open(path, "rb") as f:
            if f.read(4) != b"IB3N":
                return False

            version_b = f.read(2)
            if len(version_b) != 2:
                raise ValueError("version truncated")
            version = struct.unpack("<H", version_b)[0]
            if version != 1:
                warn(f"[ib3n] unsupported version={version} {path}")
                return True

            name = read_string(f)
            value_b = f.read(4)
            if len(value_b) != 4:
                raise ValueError("value truncated")
            value = struct.unpack("<I", value_b)[0]
            version_key = read_string(f)

            if f.read(1):
                warn(f"[ib3n] trailing bytes in {path}")

        dbg(f"[ib3n] inventory name={name} value={value} key={version_key}")
        return True
    except Exception as e:
        err(f"[ib3n] {path} error: {e}")
        traceback.print_exc()
        return False

def extract_bxml(path: str, rel: str):
    import os, struct

    def u32(b, o): return struct.unpack_from('<I', b, o)[0]
    def u16(b, o): return struct.unpack_from('<H', b, o)[0]

    def parse_lmxb(data, pos, max_end=None):
        """Parse LMXB at `pos` in `data`. Returns (end, strings, attrs, elems) or None."""
        NONE = 0x7FFFFFFF
        if data[pos:pos + 4] != b"LMXB":
            return None
        limit = len(data) if max_end is None else min(max_end, len(data))
        if pos + 16 > limit:
            return None
        nA, nE, nS = struct.unpack_from("<3I", data, pos + 4)
        aOff = pos + 16
        eOff = aOff + nA * 8
        sOff = eOff + nE * 24
        if sOff > limit:
            return None

        strings, off = [], sOff
        for _ in range(nS):
            end = data.find(b"\x00", off, limit)
            if end < 0:
                return None
            strings.append(data[off:end].decode("utf-8", "replace"))
            off = end + 1

        attrs = [struct.unpack_from("<2I", data, aOff + i * 8) for i in range(nA)]
        elems = [struct.unpack_from("<6I", data, eOff + i * 24) for i in range(nE)]
        return off, strings, attrs, elems

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
            p = data.find(b"LMXB", pos, end_limit)
            if p == -1:
                break
            result = parse_lmxb(data, p, end_limit)
            if result is None:
                warn(f"[bxml] invalid LMXB header at offset 0x{p:X}; continuing scan")
                pos = p + 4
                continue
            b, strings, attrs, elems = result
            a = max(0, p - 4)
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
            pos = b

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
    try:
        if extract_single(path):
            return True
        if extract_ib3n(path, rel):
            return True

        bundle_result = extract_bundle(path)
        if bundle_result is True:
            return True
        if bundle_result is None:
            return False

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
    """Relocate loose files (._<md5>) to their final paths using toc files.

    Bundle members are already written to their final path by extract_bundle.
    This pass handles the 18k+ loose files whose path is only known via toc.

    Toc entries are relative to the toc's own directory.
    E.g. toc at export_win32/anims/characters/__toc with line
         "chimera_hit.nac|f|<hash>" means the file belongs at
         export_win32/anims/characters/chimera_hit.nac
    """
    # Phase 0: move loose toc files from root to their proper directories.
    # Loose toc files are named like: export_win32_anims_characters___toc._<md5>
    # The directory is encoded in the filename with _ replacing /.
    # We use the root toc's directory list to disambiguate underscores in dir names.
    root_toc_dirs = set()
    for fn in os.listdir(OUTPUT_ROOT):
        if not re.search(r"___toc\._[0-9a-fA-F]{32}$", fn):
            continue
        if fn.startswith("export_win32_"):
            continue  # skip the per-dir tocs, we only want root tocs for dir list
        fp = os.path.normpath(os.path.join(OUTPUT_ROOT, fn))
        try:
            with open(fp, "r", encoding="utf-8-sig") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split("|")
                    if len(parts) == 3 and parts[1] == "d":
                        root_toc_dirs.add(_sanitize_rel(parts[0]))
        except Exception:
            pass

    # Build lookup: underscore-form of full path -> actual path
    # e.g. "export_win32_anims_characters" -> "export_win32/anims/characters"
    dir_lookup = {}
    for d in root_toc_dirs:
        dir_lookup[d.replace("/", "_")] = d

    toc_moved = 0
    for fn in os.listdir(OUTPUT_ROOT):
        if not fn.startswith("export_win32_"):
            continue
        m = re.match(r"^(.+?)___toc\._[0-9a-fA-F]{32}$", fn)
        if not m:
            continue
        stem = m.group(1)
        if stem in dir_lookup:
            target_dir = os.path.join(OUTPUT_ROOT, dir_lookup[stem])
            os.makedirs(target_dir, exist_ok=True)
            target = os.path.join(target_dir, "__toc")
            if os.path.normcase(os.path.join(OUTPUT_ROOT, fn)) != os.path.normcase(target):
                os.replace(os.path.join(OUTPUT_ROOT, fn), target)
                toc_moved += 1

    if toc_moved:
        info(f"[toc] relocated {toc_moved} loose toc files to proper directories")

    # Phase 1: find all __toc files and build hash -> full_path map
    hash_to_paths = {}
    toc_files = set()
    file_records = 0
    archive_records = 0

    for root, _, files in os.walk(OUTPUT_ROOT):
        for fn in files:
            if "__toc" not in fn.lower():
                continue
            fp = os.path.normpath(os.path.join(root, fn))
            toc_files.add(fp)

            # The directory this toc describes (relative to OUTPUT_ROOT)
            toc_dir = os.path.relpath(root, OUTPUT_ROOT)
            if toc_dir == ".":
                toc_dir = ""

            try:
                with open(fp, "r", encoding="utf-8-sig") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        parts = line.split("|")
                        if len(parts) != 3 or parts[1] not in ("d", "f"):
                            continue
                        entry_name = _sanitize_rel(parts[0])
                        if not entry_name:
                            continue
                        kind = parts[1]
                        content_hash = parts[2].strip().lower()

                        # Build full path: toc_dir/entry_name
                        if toc_dir:
                            full_path = _sanitize_rel(f"{toc_dir}/{entry_name}")
                        else:
                            full_path = entry_name

                        if kind == "f":
                            file_records += 1
                            if full_path.lower().endswith(".nb"):
                                archive_records += 1
                                continue
                            hash_to_paths.setdefault(
                                content_hash, []
                            ).append(full_path)
            except Exception as e:
                err(f"[toc] parse {fp}: {e}")
                continue

    info(
        f"[toc] {len(hash_to_paths)} hashes | "
        f"{file_records} file records | "
        f"archives skipped={archive_records}"
    )

    # Phase 2: find all loose files with ._\<md5\> suffix
    hash_sources = {}
    for root, _, files in os.walk(OUTPUT_ROOT):
        for fn in files:
            fp = os.path.normpath(os.path.join(root, fn))
            if fp in toc_files:
                continue
            match = re.search(r"\._([0-9a-fA-F]{32})$", fn)
            if not match:
                continue
            content_hash = match.group(1).lower()
            hash_sources.setdefault(content_hash, []).append(fp)

    # Phase 3: match and relocate
    moved = aliases = missing = 0
    bxml_hashes = set()
    for content_hash, paths in hash_to_paths.items():
        sources = hash_sources.get(content_hash, [])
        materialized = None

        if sources:
            primary_target = os.path.normpath(
                os.path.join(OUTPUT_ROOT, paths[0])
            )
            source = sources[0]
            os.makedirs(os.path.dirname(primary_target), exist_ok=True)
            if os.path.normcase(source) == os.path.normcase(primary_target):
                materialized = primary_target
            else:
                os.replace(source, primary_target)
                materialized = primary_target
                moved += 1
        else:
            # File might already be at its final path (from bundle extraction)
            for rel_path in paths:
                candidate = os.path.normpath(
                    os.path.join(OUTPUT_ROOT, rel_path)
                )
                if os.path.isfile(candidate):
                    materialized = candidate
                    break

        if materialized is None:
            missing += len(paths)
            continue

        # Extract bxml if needed
        if content_hash not in bxml_hashes:
            bxml_hashes.add(content_hash)
            try:
                with open(materialized, "rb") as f:
                    signature = f.read(4)
                if signature in (b"KCAP", b"PBXM"):
                    extract_bxml(materialized, paths[0])
            except Exception as e:
                warn(
                    f"[toc] bxml extraction failed h={content_hash}: {e}"
                )

        # Create aliases for duplicate paths
        for rel_path in paths:
            target = os.path.normpath(os.path.join(OUTPUT_ROOT, rel_path))
            if os.path.normcase(target) == os.path.normcase(materialized):
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copyfile(materialized, target)
            aliases += 1

        # Remove duplicate sources
        for duplicate in sources[1:]:
            if os.path.normcase(duplicate) == os.path.normcase(materialized):
                continue
            if os.path.exists(duplicate):
                os.remove(duplicate)

    # Report unmatched loose files
    unmatched = 0
    for content_hash, sources in hash_sources.items():
        if content_hash in hash_to_paths:
            continue
        for source in sources:
            unmatched += 1
            warn(
                f"[toc] no match h={content_hash} "
                f"fn={os.path.relpath(source, OUTPUT_ROOT)}"
            )

    ok(
        f"[toc] primary={moved} aliases={aliases} "
        f"unmatched={unmatched} missing={missing}"
    )

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
