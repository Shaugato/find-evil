#!/usr/bin/env bash
# G4: build llama-cpp-python with CUDA for Pascal sm_61 in the isolated test
# venv. CUDA 12.x is the last toolkit line supporting sm_61 (dropped in 13.0).
# Prebuilt cu124 wheels SIGILL on this machine, so source build is required.
set -euo pipefail

VENV=/tmp/gputest-venv
if [ ! -x "$VENV/bin/pip" ]; then
  rm -rf "$VENV"
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q --upgrade pip
fi

# 1. NVIDIA WSL-Ubuntu CUDA repo + toolkit 12.6 (compiler only; driver comes
#    from Windows host per WSL2 model)
if ! command -v /usr/local/cuda-12.6/bin/nvcc >/dev/null 2>&1; then
  cd /tmp
  wget -q https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/cuda-keyring_1.1-1_all.deb
  dpkg -i cuda-keyring_1.1-1_all.deb >/dev/null
  apt-get update -qq
  apt-get install -y -qq cuda-toolkit-12-6 cmake ninja-build git >/dev/null
fi
export PATH=/usr/local/cuda-12.6/bin:$PATH
export CUDACXX=/usr/local/cuda-12.6/bin/nvcc
nvcc --version | tail -1

# 2. Rebuild llama-cpp-python 0.3.21 (prod-pinned) with CUDA sm_61
export CMAKE_ARGS="-DGGML_CUDA=on -DCMAKE_CUDA_ARCHITECTURES=61"
export FORCE_CMAKE=1
"$VENV/bin/pip" uninstall -y -q llama-cpp-python 2>/dev/null || true
"$VENV/bin/pip" install -q --no-cache-dir --no-binary llama-cpp-python \
  "llama-cpp-python==0.3.21" 2>&1 | tail -3

# 3. Smoke test: gpu offload + model load + short generation
export LD_LIBRARY_PATH="/usr/local/cuda-12.6/lib64:${LD_LIBRARY_PATH:-}"
"$VENV/bin/python" - <<'EOF'
import time
import llama_cpp
print("version:", llama_cpp.__version__)
print("gpu_offload:", llama_cpp.llama_supports_gpu_offload())
t0 = time.time()
llm = llama_cpp.Llama(
    model_path="/opt/findevil/data/models/Llama-3.2-3B-Instruct-Q4_K_M.gguf",
    n_gpu_layers=28, n_ctx=512, verbose=False,
)
print(f"model load: {time.time()-t0:.1f}s")
for label in ("warm-up", "timed"):
    t0 = time.time()
    out = llm("The capital of France is", max_tokens=8, temperature=0)
    print(f"{label}: {out['choices'][0]['text'].strip()!r} {(time.time()-t0)*1000:.0f} ms")
EOF
echo "=== BUILD+TEST OK ==="
