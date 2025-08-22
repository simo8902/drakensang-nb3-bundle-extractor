# NB3 Bundle Extractor for DSO

Supports Nebula2 structure

- Meshes → .nvx2
- Models → .n3
- Animations → .nax3 / .nac
- Shaders → PDHS (SM3.0 bytecode)
- Sequences → .pbxml (LMXB binary XML + .bxml tables)
- Data → .bin
- Maps → .col / .db4 / .map 
    - CPAM → collision packages
    - IPAM → instance packages
    - MOSD → model/scene object data
	
## Usage  
```bash
python main.py bundle_file.nb._<hash> [more_bundles...]
```

base: August 22, 2025
License: WTFPL