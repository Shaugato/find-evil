#!/usr/bin/env bash
# G4: test prebuilt cu124 llama-cpp-python wheel in an isolated venv before
# touching the production venv. Pascal sm_61 support is the open question.
set -euo pipefail
VENV=/tmp/gputest-venv

if [ ! -d "$VENV" ]; then
  python3 -m venv "$VENV"
fi
"$VENV/bin/pip" install -q --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu124 \
  "llama-cpp-python==0.3.28" nvidia-cuda-runtime-cu12 nvidia-cublas-cu12 2>&1 | tail -2

NVLIB="$VENV/lib/python3.12/site-packages/nvidia"
export LD_LIBRARY_PATH="$NVLIB/cuda_runtime/lib:$NVLIB/cublas/lib:${LD_LIBRARY_PATH:-}"

"$VENV/bin/python" - <<'EOF'
import time
import llama_cpp
print("version:", llama_cpp.__version__)
ok = llama_cpp.llama_supports_gpu_offload()
print("gpu_offload:", ok)
if not ok:
    raise SystemExit("wheel has no GPU support")

t0 = time.time()
llm = llama_cpp.Llama(
    model_path="/opt/findevil/data/models/Llama-3.2-3B-Instruct-Q4_K_M.gguf",
    n_gpu_layers=28, n_ctx=512, verbose=True,
)
print(f"model load: {time.time()-t0:.1f}s")
t0 = time.time()
out = llm("The capital of France is", max_tokens=8, temperature=0)
dt = time.time() - t0
print("inference:", out["choices"][0]["text"].strip(), f"({dt*1000:.0f} ms total)")
EOF
