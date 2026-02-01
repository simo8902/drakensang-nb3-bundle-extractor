# NB3 Bundle Extractor for DSO

![GitHub repo size](https://img.shields.io/github/repo-size/simo8902/drakensang-nb3-bundle-extractor)
![GitHub last commit](https://img.shields.io/github/last-commit/simo8902/drakensang-nb3-bundle-extractor)
![GitHub license](https://img.shields.io/github/license/simo8902/drakensang-nb3-bundle-extractor)

### version_history

- added explicit support for not bundled files \
- split extraction into two steps: first extract everything, then sort files into correct folders \
- added TOC-based sorting that reads TOC files to know where each file belongs \
- files without a TOC entry just get their hash removed from the filename \
- fixed file moving on Windows when the output file already exists \

WARNING: for cur version of the game data, please delete the cached data fully(DSOClient from Temp), \
then redownload then use the script to parse it

### Extracts:

- The following tags: **_B3NHB3N**, **__ZN**, **IB3N**, **_TOC** \
- TODO: The following are not yet tested: **KCAP**,**LMXB** \
(name_len(u16 @0x08) + name(UTF-8) + padding/u32 + repeated) \
- The **shaders_sm30**, is a nighmare hell for reversing, however I get somewhere \
- Using **SM3.0 bytecode** obv \
- The fourcc in the file are: FXLC, CTAB, HLSL, CLIT, PRES, PRSI, \ 
PUVS, MLPU, **PDHS** is the header fourcc, MLPS, SSMT, PSSM, ESMD \
(however some of them may or may not be valid) \
- File size: 0x0016B506 bytes 
```bash
python shaders.py --dedup shaders_sm30 folderName
```
P.S. Im not continuing this shader reversing shit sry. \
U see the shader names used, thats enough. U can write them yourself \

⚠️ Disclaimer
The script will need a lot of time!
This is not datamining for exploits or gameplay hacks
Use it responsibly
Respect the game

## Usage  
simple asf

# neb.py
```bash
py neb.py
```
auto-scans input/ folder recursively for data files

# bank.py
```
py bank.py <file1.bank> [file2.bank ...]
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