#!/usr/bin/env bash
# Integrity-check the downloaded Rocba-Memory.zip
ZIP="/mnt/c/Users/shaug/Downloads/Rocba-Memory.zip"
ls -l "$ZIP"
/opt/findevil/venv/bin/python - <<'EOF'
import zipfile
z = zipfile.ZipFile("/mnt/c/Users/shaug/Downloads/Rocba-Memory.zip")
for i in z.infolist():
    print(f"entry: {i.filename}  compressed={i.compress_size/1e9:.2f}GB raw={i.file_size/1e9:.2f}GB")
bad = z.testzip()
print("testzip bad entry:", bad)
EOF
