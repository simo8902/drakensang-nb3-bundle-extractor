# NB3 Bundle Extractor for DSO

![GitHub repo size](https://img.shields.io/github/repo-size/simo8902/drakensang-nb3-bundle-extractor)
![GitHub last commit](https://img.shields.io/github/last-commit/simo8902/drakensang-nb3-bundle-extractor)
![GitHub license](https://img.shields.io/github/license/simo8902/drakensang-nb3-bundle-extractor)

### Extracts:

- Meshes -> .nvx2
- Models -> .n3
- Animations -> .nax3 / .nac
- Audio -> `.bank` → `WAVE` (1536kbps, pure 🔥)
- Shaders -> PDHS (SM3.0 bytecode)
- Sequences -> .pbxml (LMXB binary XML + .bxml tables)
- Data -> .bin
- Maps -> .col / .db4 / .map 
    - CPAM -> collision packages
    - IPAM -> instance packages
    - MOSD -> model/scene object data

WARNING: 
Some of this data has been fully removed from production servers.
This archive preserves what the game has forgotten

⚠️ Disclaimer
This is not datamining for exploits or gameplay hacks
It’s pure asset-level archival of forgotten map content for preservation and curiosity
Use it responsibly
Respect the game
Document the past

## Usage  
simple asf

# neb.py
```bash
py neb.py
```
auto-scans input/ folder recursively for *.nb._* files

# bank.py
```
py bank.py <file1.bank> [file2.bank ...]
```

# sigunature_check.py
```
python sigunature_check.py <file1.bank> [file2.bank ...]
```

# diff.py
```
py {inputFROM} {inputWith} out.txt
```

# copy.ps1
change $src to the path u have new data containing bundles obv\
$listFile with the input file for compare 

prod. by simo 🖤\
base: August 22, 2025\
License: WTFPL