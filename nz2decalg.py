import lzma, struct, sys

data = open(sys.argv[1], "rb").read()
props = data[4]
dict_size = struct.unpack("<I", data[5:9])[0]
compressed = data[13:]

lc = props % 9
lp = (props // 9) % 5
pb = props // 9 // 5

filters = [
    {"id": lzma.FILTER_X86},
    {"id": lzma.FILTER_LZMA1, "dict_size": dict_size, "lc": lc, "lp": lp, "pb": pb}
]
dec = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=filters)
output = dec.decompress(compressed)
open(sys.argv[2], "wb").write(output)
print(f"ok {len(output)} bytes")