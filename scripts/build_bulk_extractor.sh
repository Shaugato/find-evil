#!/usr/bin/env bash
# Build bulk_extractor 2.1.1 from the release tarball on Ubuntu 24.04 (G3).
# bulk-extractor was dropped from Debian/Ubuntu repos; source build is the
# current supported path per github.com/simsong/bulk_extractor wiki.
set -euo pipefail

VER=2.1.1
WORK=/tmp/be-build
mkdir -p "$WORK"
cd "$WORK"

apt-get install -y -qq build-essential autoconf automake libtool \
  libssl-dev libewf-dev libexpat1-dev zlib1g-dev flex pkg-config \
  libsqlite3-dev libre2-dev >/dev/null

if [ ! -f "bulk_extractor-${VER}.tar.gz" ]; then
  wget -q "https://github.com/simsong/bulk_extractor/releases/download/v${VER}/bulk_extractor-${VER}.tar.gz"
fi
tar xzf "bulk_extractor-${VER}.tar.gz"
cd "bulk_extractor-${VER}"
./configure --quiet
make -j"$(nproc)" >/dev/null
make install >/dev/null
echo "=== installed ==="
bulk_extractor -V
