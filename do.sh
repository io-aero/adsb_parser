#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<EOF
Usage: $0 <option>

Options:
  mamba    Create/update the mamba environment from environment.yml
  help     Show this help message

More options may be added in the future.
EOF
}

cmd_mamba() {
  if command -v micromamba &>/dev/null; then
    micromamba env create -f environment.yml 2>/dev/null || micromamba env update -f environment.yml --prune
  else
    echo "error: micromamba not found. Install micromamba or use conda." >&2
    exit 1
  fi
}

case "${1:-help}" in
  mamba)  cmd_mamba ;;
  help)   usage ;;
  -h|--help) usage ;;
  *)
    echo "Unknown option: $1" >&2
    echo ""
    usage
    exit 1
    ;;
esac
