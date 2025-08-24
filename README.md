# NB3 Bundle Extractor for DSO

Supports Nebula2/3 structure

### Extracts:

- Meshes -> .nvx2
- Models -> .n3
- Animations -> .nax3 / .nac
- Audio -> `.bank` → `WAVE` (1536kbps, pure 🔥)
fck b**p**nt for deleting my dream music!! bi**hes
- Shaders -> PDHS (SM3.0 bytecode)
- Sequences -> .pbxml (LMXB binary XML + .bxml tables)
- Data -> .bin
- Maps -> .col / .db4 / .map 
    - CPAM -> collision packages
    - IPAM -> instance packages
    - MOSD -> model/scene object data
And more to be revealed, kidding, I dont have time:

File: DRO MUSIC SIGNATURES 
contains MAPPING STAMP of the data from 2020
includes all deleted maps, music and so on, still in process of reversing

SOON: 3D MAP MODELS, FOR ALL DELETED TERRAINS LIKE OUR BELOVED "OCEAN OF BONES"

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

# extract.py
```bash
py neb.py
```

# bank.py
```
py bank_extract.py <file1.bank> [file2.bank ...]
```
auto-scans input/ folder recursively for *.nb._* files

# toc.py
```
py toc.py
```
auto-scans input/ folder recursively for *.toc._* files

# sigunature_check.py
```
python sigunature_check.py <file1.bank> [file2.bank ...]
```

prod. by simo 🖤
base: August 22, 2025
License: WTFPL