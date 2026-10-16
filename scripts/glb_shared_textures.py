#!/usr/bin/env python3
"""Point the textures embedded in GLB files at one shared copy in godot/assets/textures.

The squares and the route all embed the same brick/paving textures (byte-identical copies of
assets/textures/*.png). Godot extracts embedded images per model, so every texture ended up in the
build up to three times. This rewrites each embedded image into an external reference to
../textures/<name>.png (only when the embedded bytes match that file exactly, so nothing changes
visually), and drops the embedded bytes from the binary chunk.

Usage: glb_shared_textures.py <textures dir> <file.glb>...
"""
import json
import os
import struct
import sys


def pad(b: bytes, fill: bytes) -> bytes:
    return b + fill * (-len(b) % 4)


def rewrite(path: str, tex_dir: str) -> int:
    data = open(path, 'rb').read()
    magic, version, _ = struct.unpack('<4sII', data[:12])
    assert magic == b'glTF' and version == 2, path
    jlen = struct.unpack('<I', data[12:16])[0]
    gltf = json.loads(data[20:20 + jlen])
    blen = struct.unpack('<I', data[20 + jlen:24 + jlen])[0]
    binary = data[28 + jlen:28 + jlen + blen]
    views = gltf.get('bufferViews', [])

    dropped = set()
    for im in gltf.get('images', []):
        if 'bufferView' not in im:
            continue
        v = views[im['bufferView']]
        start = v.get('byteOffset', 0)
        src = os.path.join(tex_dir, im.get('name', '') + '.png')
        if os.path.exists(src) and open(src, 'rb').read() == binary[start:start + v['byteLength']]:
            dropped.add(im.pop('bufferView'))
            im.pop('mimeType', None)
            im['uri'] = '../textures/' + os.path.basename(src)
    if not dropped:
        return 0

    # rebuild the binary chunk without the image views, renumbering the views that stay
    new_bin = b''
    remap = {}
    kept = []
    for i, v in enumerate(views):
        if i in dropped:
            continue
        start = v.get('byteOffset', 0)
        chunk = binary[start:start + v['byteLength']]
        new_bin = pad(new_bin, b'\0')
        v['byteOffset'] = len(new_bin)
        new_bin += chunk
        remap[i] = len(kept)
        kept.append(v)
    gltf['bufferViews'] = kept
    for a in gltf.get('accessors', []):
        if 'bufferView' in a:
            a['bufferView'] = remap[a['bufferView']]
        sparse = a.get('sparse')
        if sparse:
            sparse['indices']['bufferView'] = remap[sparse['indices']['bufferView']]
            sparse['values']['bufferView'] = remap[sparse['values']['bufferView']]
    for im in gltf.get('images', []):
        if 'bufferView' in im:
            im['bufferView'] = remap[im['bufferView']]
    new_bin = pad(new_bin, b'\0')
    gltf['buffers'][0]['byteLength'] = len(new_bin)

    js = pad(json.dumps(gltf, separators=(',', ':')).encode(), b' ')
    out = struct.pack('<4sII', b'glTF', 2, 12 + 8 + len(js) + 8 + len(new_bin))
    out += struct.pack('<I4s', len(js), b'JSON') + js + struct.pack('<I4s', len(new_bin), b'BIN\0') + new_bin
    open(path, 'wb').write(out)
    return len(dropped)


if __name__ == '__main__':
    tex_dir = sys.argv[1]
    for p in sys.argv[2:]:
        print(f'{os.path.basename(p)}: {rewrite(p, tex_dir)} textures now shared')
