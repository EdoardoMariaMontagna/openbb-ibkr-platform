#!/usr/bin/env bash
# Scan installed dependencies for known CVEs with pip-audit.
# Run with your project virtualenv activated (needs the `dev` extras:
# pip install -e ".[dev]").
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

if ! command -v pip-audit >/dev/null 2>&1; then
  echo "error: pip-audit not found. Install dev extras first: pip install -e \".[dev]\"" >&2
  exit 1
fi

echo "Scanning the active environment for known vulnerabilities..."
pip-audit --progress-spinner off
