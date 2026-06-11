#!/usr/bin/env bash
echo "=== llamacpp unit ==="
cat /etc/systemd/system/findevil-llamacpp.service 2>/dev/null
echo "=== nvcc ==="
nvcc --version 2>&1 | tail -2
ls /usr/local/cuda*/bin/nvcc 2>/dev/null
echo "=== llama_cpp version ==="
/opt/findevil/venv/bin/python - <<'EOF'
import llama_cpp
print("version:", llama_cpp.__version__)
try:
    print("gpu_offload:", llama_cpp.llama_supports_gpu_offload())
except Exception as exc:
    print("gpu_offload check failed:", exc)
EOF
echo "=== models on disk ==="
ls -la /opt/findevil/data/models/ 2>/dev/null
echo "=== llamacpp service logs (tail) ==="
journalctl -u findevil-llamacpp.service -n 15 --no-pager 2>/dev/null | tail -15
