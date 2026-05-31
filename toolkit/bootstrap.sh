#!/usr/bin/env bash
# bootstrap.sh — set up the environment to "run" the HP methodology.
#
# Installs the tools the toolkit and its renderers need. User-space only;
# does not require sudo. Idempotent — safe to re-run; only installs what's
# missing.
#
# Tools installed:
#   - uv      Python project/env manager (Astral). Powers the eventual hp_toolkit Python package.
#   - d2      Declarative diagrams (renders .d2 → .svg, .png). Used for one of our presentation views.
#   - mmdc    Mermaid CLI (renders .mmd / fenced mermaid → .svg, .png). Used to render mermaid views without VSCode.
#
# Future additions (deferred until needed):
#   - Python deps via `uv sync` once pyproject.toml exists
#   - graphviz (if HP visualizations need dot-style layouts)
#   - excalidraw-cli or similar (if Excalidraw views become a first-class view)
#
# Usage:
#   bash bootstrap.sh
#
# Override install location:
#   HP_INSTALL_DIR=~/somewhere/bin bash bootstrap.sh
#
# Last updated: 2026-05-22

set -euo pipefail

INSTALL_DIR="${HP_INSTALL_DIR:-$HOME/.local/bin}"
mkdir -p "$INSTALL_DIR"

color() { printf '\033[%sm%s\033[0m' "$1" "$2"; }
section() { echo; echo "$(color 1 "==> $1")"; }
ok()      { echo "  $(color 32 "✓") $1"; }
miss()    { echo "  $(color 33 "•") $1"; }
fail()    { echo "  $(color 31 "✗") $1"; }

section "Checking PATH"
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
  miss "$INSTALL_DIR is not on \$PATH"
  echo "      Add this line to your shell rc (~/.bashrc, ~/.zshrc, etc.):"
  echo "          export PATH=\"$INSTALL_DIR:\$PATH\""
  echo "      Tools installed below will land in $INSTALL_DIR. They won't be"
  echo "      reachable from your shell until that line is in place."
else
  ok "$INSTALL_DIR is on \$PATH"
fi
# Ensure this script's child processes see the install dir
export PATH="$INSTALL_DIR:$PATH"

section "uv (Python project/env manager)"
if command -v uv &>/dev/null; then
  ok "uv installed: $(uv --version 2>&1)"
else
  miss "uv missing — installing via Astral's official script"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # uv installer adds itself to ~/.cargo/bin or ~/.local/bin depending on env
  export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
  if command -v uv &>/dev/null; then
    ok "uv installed: $(uv --version 2>&1)"
  else
    fail "uv install did not put binary on PATH — check ~/.cargo/bin and ~/.local/bin"
  fi
fi

section "Python project sync"
if [[ -f pyproject.toml ]]; then
  echo "  pyproject.toml found — running 'uv sync'"
  uv sync
  ok "Python deps synced"
else
  miss "pyproject.toml not yet present (deferred until Python code lands)"
fi

section "d2 (declarative diagrams)"
if command -v d2 &>/dev/null; then
  ok "d2 installed: $(d2 --version 2>&1 | head -1)"
else
  miss "d2 missing — installing to $INSTALL_DIR"
  # Official installer; -d sets install directory
  curl -fsSL https://d2lang.com/install.sh | sh -s -- -d "$INSTALL_DIR"
  if command -v d2 &>/dev/null; then
    ok "d2 installed: $(d2 --version 2>&1 | head -1)"
  else
    fail "d2 install did not land on PATH — verify $INSTALL_DIR/d2 exists"
  fi
fi

section "mmdc (Mermaid CLI)"
if command -v mmdc &>/dev/null; then
  ok "mmdc installed"
else
  if command -v npm &>/dev/null; then
    miss "mmdc missing — installing via npm into $HOME/.local"
    npm install --prefix "$HOME/.local" @mermaid-js/mermaid-cli >/dev/null 2>&1
    # npm prefix install puts binaries in $prefix/bin
    if [[ -x "$HOME/.local/bin/mmdc" ]]; then
      ok "mmdc installed at $HOME/.local/bin/mmdc"
    else
      fail "mmdc install did not produce a binary — check npm output"
    fi
  else
    fail "npm not found — Node.js required for mmdc. Install Node first, then re-run."
  fi
fi

section "Summary"
for tool in uv d2 mmdc; do
  if command -v $tool &>/dev/null; then
    ok "$tool"
  else
    fail "$tool (not installed)"
  fi
done
echo
echo "Next: see toolkit/README.md for usage."
