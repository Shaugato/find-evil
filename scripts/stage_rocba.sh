#!/usr/bin/env bash
# Stage the official ROCBA memory image into WSL ext4 for analysis.
set -euo pipefail
ZIP="/mnt/c/Users/shaug/Downloads/Rocba-Memory.zip"
DEST="/opt/findevil/data/cases/rocba"

echo "=== zip contents ==="
/opt/findevil/venv/bin/python - <<'EOF'
import zipfile
z = zipfile.ZipFile("/mnt/c/Users/shaug/Downloads/Rocba-Memory.zip")
for i in z.infolist():
    print(f"{i.filename}  {i.file_size/1e9:.2f} GB")
EOF

mkdir -p "$DEST"
echo "=== extracting inner 7z (STORED, salvage past CRC mismatch) ==="
# The outer zip stores the .7z uncompressed; pull the member bytes directly
# even though the trailing CRC is wrong, then let 7z verify the real payload.
/opt/findevil/venv/bin/python - <<'EOF'
import os, struct, zlib, zipfile
zip_path = "/mnt/c/Users/shaug/Downloads/Rocba-Memory.zip"
dest = "/opt/findevil/data/cases/rocba/Rocba-Memory.7z"
os.makedirs(os.path.dirname(dest), exist_ok=True)
z = zipfile.ZipFile(zip_path)
info = z.infolist()[0]
print("compress_type:", info.compress_type, "(8=deflate)")
with open(zip_path, "rb") as f:
    f.seek(info.header_offset)
    hdr = f.read(30)
    sig = struct.unpack("<I", hdr[:4])[0]
    assert sig == 0x04034b50, hex(sig)
    n_len, e_len = struct.unpack("<HH", hdr[26:30])
    f.seek(info.header_offset + 30 + n_len + e_len)
    d = zlib.decompressobj(-zlib.MAX_WBITS)
    remaining = info.compress_size
    written = 0
    with open(dest, "wb") as out:
        try:
            while remaining:
                chunk = f.read(min(8 * 1024 * 1024, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                data = d.decompress(chunk)
                out.write(data); written += len(data)
            tail = d.flush()
            out.write(tail); written += len(tail)
        except zlib.error as exc:
            print("zlib stopped early:", exc)
print(f"decompressed {written} bytes, expected {info.file_size}")
EOF
apt-get install -y -qq p7zip-full >/dev/null 2>&1 || true
echo "=== 7z test ==="
7z t "$DEST/Rocba-Memory.7z" 2>&1 | tail -8 || true
echo "=== 7z extract ==="
7z x -y -o"$DEST" "$DEST/Rocba-Memory.7z" 2>&1 | tail -8 || true

chown -R findevil:findevil /opt/findevil/data/cases 2>/dev/null || true
chmod -R u+rwX,g+rX "$DEST"
echo "=== staged files ==="
find "$DEST" -type f -exec ls -lh {} \;
echo "=== sha256 (provenance) ==="
sha256sum "$ZIP"
find "$DEST" -type f -size +100M -exec sha256sum {} \;
