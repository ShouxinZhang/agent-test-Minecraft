#!/usr/bin/env bash
set -euo pipefail

SHARED_ROOT="${SHARED_ROOT:-$HOME/Documents/GitHub/.shared-python-envs}"
SHARED_ENV_NAME="${SHARED_ENV_NAME:-py314-torch-cu130}"
PYTHON_BIN="${PYTHON_BIN:-python3.14}"
TORCH_INDEX_URL="${TORCH_INDEX_URL:-https://download.pytorch.org/whl/cu130}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
HOST_PROFILE_PATH="${HOST_PROFILE_PATH:-$SKILL_DIR/HOST_PROFILE.md}"

SHARED_ENV_DIR="$SHARED_ROOT/$SHARED_ENV_NAME"
REPORT_DIR="$SHARED_ROOT/reports"

timestamp() {
  date +"%Y%m%d-%H%M%S"
}

trim() {
  local s="$1"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf "%s" "$s"
}

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "[ERROR] Missing command: $cmd" >&2
    exit 1
  fi
}

collect_host_report() {
  mkdir -p "$REPORT_DIR"
  local report_file="$REPORT_DIR/host-$(timestamp).md"

  {
    echo "# Host Report"
    echo
    echo "- Time: $(date -Iseconds)"
    echo "- Host: $(hostname)"
    echo "- Kernel: $(uname -srmo)"
    echo
    echo "## CPU"
    if command -v lscpu >/dev/null 2>&1; then
      lscpu
    else
      echo "lscpu not found"
    fi
    echo
    echo "## Memory"
    if command -v free >/dev/null 2>&1; then
      free -h
    else
      echo "free not found"
    fi
    echo
    echo "## GPU"
    if command -v nvidia-smi >/dev/null 2>&1; then
      nvidia-smi
    else
      echo "nvidia-smi not found (no NVIDIA GPU driver or command missing)"
    fi
    echo
    echo "## Disk"
    df -h "$HOME/Documents/GitHub" || true
  } >"$report_file"

  echo "[OK] Host report saved: $report_file"
}

write_host_profile_snapshot() {
  mkdir -p "$(dirname "$HOST_PROFILE_PATH")"

  local os_line
  local cpu_model
  local cores
  local threads
  local cpu_max_mhz
  local mem_total
  local swap_total
  local gpu_name="N/A"
  local gpu_vram="N/A"
  local driver_version="N/A"
  local cuda_version="N/A"

  os_line="$(uname -srmo 2>/dev/null || echo "unknown")"
  cpu_model="$(trim "$(lscpu 2>/dev/null | awk -F: '/Model name/{print $2; exit}')")"
  cores="$(trim "$(lscpu 2>/dev/null | awk -F: '/Core\(s\) per socket/{print $2; exit}')")"
  threads="$(trim "$(lscpu 2>/dev/null | awk -F: '/CPU\(s\)/{print $2; exit}')")"
  cpu_max_mhz="$(trim "$(lscpu 2>/dev/null | awk -F: '/CPU max MHz/{print $2; exit}')")"
  mem_total="$(trim "$(free -h 2>/dev/null | awk '/^Mem:/{print $2; exit}')")"
  swap_total="$(trim "$(free -h 2>/dev/null | awk '/^Swap:/{print $2; exit}')")"

  if command -v nvidia-smi >/dev/null 2>&1; then
    local gpu_query
    gpu_query="$(nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader 2>/dev/null | head -n 1 || true)"
    if [[ -n "$gpu_query" ]]; then
      IFS=',' read -r gpu_name driver_version gpu_vram <<< "$gpu_query"
      gpu_name="$(trim "$gpu_name")"
      driver_version="$(trim "$driver_version")"
      gpu_vram="$(trim "$gpu_vram")"
    fi

    cuda_version="$(nvidia-smi 2>/dev/null | sed -n 's/.*CUDA Version: \([0-9.]*\).*/\1/p' | head -n 1)"
    cuda_version="$(trim "$cuda_version")"
    if [[ -z "$cuda_version" ]]; then
      cuda_version="N/A"
    fi
  fi

  cat >"$HOST_PROFILE_PATH" <<EOF
# Host Hardware Profile (Linux)

- Snapshot Time: $(date +"%Y-%m-%d %H:%M %z")
- OS: $os_line

## CPU

- Model: ${cpu_model:-N/A}
- Cores/Threads: ${cores:-N/A}C/${threads:-N/A}T
- Max Frequency: ${cpu_max_mhz:-N/A} MHz

## Memory

- RAM Total: ${mem_total:-N/A}
- Swap Total: ${swap_total:-N/A}

## GPU

- Model: ${gpu_name:-N/A}
- VRAM: ${gpu_vram:-N/A}
- Driver: ${driver_version:-N/A}
- CUDA (nvidia-smi): ${cuda_version:-N/A}

## Shared Env Recommendation

- Preferred stack: Python 3.14 + PyTorch stable + CUDA 13.0 wheels (\`cu130\`)
- Shared root: \`~/Documents/GitHub/.shared-python-envs\`
- Default env name: \`py314-torch-cu130\`
EOF

  echo "[OK] Host snapshot updated: $HOST_PROFILE_PATH"
}

shared_python() {
  echo "$SHARED_ENV_DIR/bin/python"
}

shared_site_packages() {
  "$(shared_python)" -c 'import site; print(next(p for p in site.getsitepackages() if p.endswith("site-packages")))'
}

cmd_init() {
  require_cmd "$PYTHON_BIN"
  mkdir -p "$SHARED_ROOT"

  collect_host_report

  if [[ ! -d "$SHARED_ENV_DIR" ]]; then
    echo "[INFO] Creating shared env: $SHARED_ENV_DIR"
    "$PYTHON_BIN" -m venv "$SHARED_ENV_DIR"
  else
    echo "[INFO] Shared env exists: $SHARED_ENV_DIR"
  fi

  echo "[INFO] Installing heavy packages in shared env"
  "$(shared_python)" -m pip install -U pip
  "$(shared_python)" -m pip install -U torch torchvision torchaudio --index-url "$TORCH_INDEX_URL"

  echo "[OK] Shared environment ready"
  cmd_doctor
}

cmd_doctor() {
  if [[ ! -x "$(shared_python)" ]]; then
    echo "[ERROR] Shared env not found: $SHARED_ENV_DIR" >&2
    exit 1
  fi

  echo "[INFO] Shared env: $SHARED_ENV_DIR"
  "$(shared_python)" - <<'PY'
import platform
import torch

print("python:", platform.python_version())
print("torch:", torch.__version__)
print("cuda available:", torch.cuda.is_available())
print("torch cuda runtime:", torch.version.cuda)
if torch.cuda.is_available():
    print("gpu:", torch.cuda.get_device_name(0))
PY
}

cmd_inspect() {
  mkdir -p "$SHARED_ROOT"
  collect_host_report
  write_host_profile_snapshot
  echo "[OK] Inspect completed (no package installation performed)."
}

cmd_attach() {
  if [[ $# -ne 1 ]]; then
    echo "Usage: $0 attach /abs/path/to/project" >&2
    exit 1
  fi

  local project_dir="$1"
  local project_venv="$project_dir/.venv"

  if [[ ! -d "$project_dir" ]]; then
    echo "[ERROR] Project dir not found: $project_dir" >&2
    exit 1
  fi

  if [[ ! -x "$(shared_python)" ]]; then
    echo "[ERROR] Shared env not found. Run init first." >&2
    exit 1
  fi

  echo "[INFO] Creating project venv: $project_venv"
  "$(shared_python)" -m venv "$project_venv"

  local shared_sp
  shared_sp="$(shared_site_packages)"

  local project_sp
  project_sp="$($project_venv/bin/python -c 'import site; print(next(p for p in site.getsitepackages() if p.endswith("site-packages")))')"

  echo "$shared_sp" >"$project_sp/_shared_heavy_packages.pth"

  echo "[OK] Attached shared site-packages"
  echo "[INFO] Shared site-packages: $shared_sp"
  echo "[INFO] Project site-packages: $project_sp"
  echo "[INFO] Activate with: source $project_venv/bin/activate"
}

usage() {
  cat <<EOF
Usage:
  $0 inspect
  $0 init
  $0 doctor
  $0 attach /abs/path/to/project

Optional env vars:
  SHARED_ROOT
  SHARED_ENV_NAME
  PYTHON_BIN
  TORCH_INDEX_URL
EOF
}

main() {
  if [[ $# -lt 1 ]]; then
    usage
    exit 1
  fi

  case "$1" in
    inspect)
      shift
      cmd_inspect "$@"
      ;;
    init)
      shift
      cmd_init "$@"
      ;;
    doctor)
      shift
      cmd_doctor "$@"
      ;;
    attach)
      shift
      cmd_attach "$@"
      ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "$@"
