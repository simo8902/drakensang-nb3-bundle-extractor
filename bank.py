import subprocess, re, os, glob, sys

mapping = {}
if os.path.exists("eventbankmapping.txt"):
    with open("eventbankmapping.txt", encoding="utf-8") as f:
        for line in f:
            if ";" in line:
                left, right = line.strip().split(";", 1)
                mapping[right] = left

if len(sys.argv) > 1:
    banks = sys.argv[1:]
else:
    banks = glob.glob("*.bank")
    if not banks:
        print("usage: py extract.py <file1.bank> [file2.bank ...]")
        sys.exit(1)

for bank in banks:
    print(f"Processing {bank}...")
    i = 1
    while True:
        proc = subprocess.Popen(
            ["vgmstream-cli.exe", bank, "-s", str(i), "-o", "tmp.wav"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        name = None
        success = False
        for line in proc.stdout:
            if "failed opening" in line:
                success = False
            m = re.search(r"stream name:\s*(.+)", line)
            if m:
                name = m.group(1).strip()
                success = True
        proc.wait()
        if not success or not os.path.exists("tmp.wav"):
            break
        if not name:
            name = f"{i}"

        if name in mapping:
            relpath = mapping[name].replace("/", os.sep)
        else:
            relpath = os.path.splitext(bank)[0] + "_" + name

        folder = os.path.join("extracted", os.path.dirname(relpath))
        os.makedirs(folder, exist_ok=True)

        basefile = re.sub(r'[<>:"/\\|?*]', "_", os.path.basename(relpath))
        final = os.path.join(folder, f"{basefile}.wav")

        if os.path.exists(final):
            k = 1
            while True:
                alt = os.path.join(folder, f"{basefile}_{k}.wav")
                if not os.path.exists(alt):
                    final = alt
                    break
                k += 1

        os.rename("tmp.wav", final)
        print(f"  Extracted {final}")
        i += 1
