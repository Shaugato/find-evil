#!/usr/bin/env bash
# G4 decision evidence: same prompt/8-token benchmark on the prod CPU wheel,
# to compare against the sm_61 CUDA build's 4.5-5.0s result.
set -euo pipefail
/opt/findevil/venv/bin/python - <<'EOF'
import time
import llama_cpp
print("version:", llama_cpp.__version__)
print("gpu_offload:", llama_cpp.llama_supports_gpu_offload())
t0 = time.time()
llm = llama_cpp.Llama(
    model_path="/opt/findevil/data/models/Llama-3.2-3B-Instruct-Q4_K_M.gguf",
    n_gpu_layers=0, n_ctx=512, n_threads=8, verbose=False,
)
print(f"model load: {time.time()-t0:.1f}s")
for label in ("warm-up", "timed"):
    t0 = time.time()
    out = llm("The capital of France is", max_tokens=8, temperature=0)
    print(f"{label}: {out['choices'][0]['text'].strip()!r} {(time.time()-t0)*1000:.0f} ms")
EOF
