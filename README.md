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
The script will need a lot of time!
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

1. Get main TOC file from current version  
   **__toc_md5hash**  
   **bundles_optional___toc_md5hash**

2. Get the same files from test server  
3. Parse them with **neb.py**  
4. Copy **diff.py** to the output directory where these TOC files are located  
5. Compare with **diff.py**  
6. Copy the new data and extract it with **neb.py**  
7. Set the path in **copy.ps1**  
   **$listFile** is the input file for compare  
   **$src** is the path with new data containing bundles  

# copy.ps1
Change **$src** to the path containing the new data (bundles)  
**$listFile** must point to the input file for comparison  


then copy the difference

prod. by simo 🖤\
base: August 22, 2025\
License: WTFPL