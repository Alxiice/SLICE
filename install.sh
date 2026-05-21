#!/bin/bash
set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMAND="${1:-install}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
info()  { echo -e "${GREEN}==>${NC} $*"; }
warn()  { echo -e "${YELLOW}WARN:${NC} $*"; }
error() { echo -e "${RED}ERROR:${NC} $*"; exit 1; }

NODE_PATHS=(
  $NODE_JS_PATH
  /usr/local/bin
  /usr/bin
  /bin
)

find_bin() {
  local name="$1"
  local result
  result=$(command -v "$name" 2>/dev/null)
  if [ -n "$result" ]; then echo "$result"; return; fi
  for dir in "${NODE_PATHS[@]}"; do
    if [ -x "$dir/$name" ]; then echo "$dir/$name"; return; fi
  done
  return 1
}

cmd_uninstall() {
  echo ""
  warn "This will:"
  warn "  - Stop and remove all CodingStack containers"
  warn "  - Remove Docker volumes (ollama models + webui data)"
  warn "  - Remove downloaded Docker images"
  warn "  - Remove .venv/mcp virtualenv"
  warn "  - Remove generated MCP config"
  echo ""
  read -rp "Are you sure? [y/N] " CONFIRM
  [[ "$CONFIRM" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }

  info "Stopping containers..."
  cd "$REPO_DIR"
  docker compose down --volumes --remove-orphans 2>/dev/null || true

  info "Removing images..."
  docker rmi ollama/ollama:latest 2>/dev/null || true
  docker rmi ghcr.io/open-webui/open-webui:main 2>/dev/null || true

  info "Removing virtualenv..."
  rm -rf "$REPO_DIR/.venv/mcp"

  info "Removing generated MCP config..."
  rm -f "$REPO_DIR/.continue/mcpServers/default-mcp-server.yaml"

  echo ""
  info "Uninstall complete."
}

cmd_install() {
  echo ""
  echo "=== CodingStack Install ==="
  echo "Repo: $REPO_DIR"
  echo ""

  # ── Requirements ──────────────────────────────────────────
  info "Checking requirements..."

  DOCKER=$(command -v docker 2>/dev/null) || error "docker not found."
  echo "  docker  : $DOCKER ($(docker --version 2>&1 | head -1))"

  docker compose version &>/dev/null || error "'docker compose' not available."
  echo "  compose : OK"

  docker info &>/dev/null || error "Docker daemon not running. Run: sudo systemctl start docker"
  echo "  daemon  : running"

  if docker info 2>/dev/null | grep -qi "nvidia"; then
    echo "  GPU     : OK"
  else
    warn "GPU not accessible from Docker. Ollama will run on CPU only."
  fi

  NPX=$(find_bin npx) || error "npx not found. Check NODE_PATHS in install.sh"
  echo "  npx     : $NPX"
  NODE_BIN="$(dirname "$NPX")"

  PYTHON=$(find_bin python3) || PYTHON=$(find_bin python) || error "python3 not found."
  echo "  python  : $PYTHON ($($PYTHON --version 2>&1))"

  GIT=$(find_bin git) || error "git not found."
  echo "  git     : $GIT"
  GIT_BIN="$(dirname "$GIT")"

  # ── Virtualenv ────────────────────────────────────────────
  echo ""
  VENV_DIR="$REPO_DIR/.venv/mcp"
  if [ ! -f "$VENV_DIR/bin/python" ]; then
    info "Creating virtualenv at .venv/mcp ..."
    "$PYTHON" -m venv "$VENV_DIR"
  else
    info "Virtualenv already exists, skipping."
  fi

  info "Installing mcp-server-git ..."
  "$VENV_DIR/bin/pip" install --quiet --upgrade mcp-server-git
  echo "  mcp-server-git : OK"

  # ── GitHub token ──────────────────────────────────────────
  echo ""
  if [ -z "$GITHUB_TOKEN" ]; then
    warn "GITHUB_TOKEN env var not set — github MCP server will not authenticate."
    warn "Set it before running: export GITHUB_TOKEN=ghp_xxx && ./install.sh install"
    GITHUB_TOKEN="REPLACE_WITH_YOUR_GITHUB_TOKEN"
  else
    echo "  GitHub token : OK"
  fi

  if [ -z "$GITHUB_TOKEN" ]; then
    warn "No GitHub token — github MCP server will not authenticate."
    GITHUB_TOKEN="REPLACE_WITH_YOUR_GITHUB_TOKEN"
  else
    echo "  GitHub token : OK"
  fi

  # ── MCP config ────────────────────────────────────────────
  echo ""
  info "Writing MCP config..."
  MCP_CONFIG="$REPO_DIR/.continue/mcpServers/default-mcp-server.yaml"
  mkdir -p "$(dirname "$MCP_CONFIG")"

  cat > "$MCP_CONFIG" << EOF
name: CodingStack Workspace
version: 1.0.0

mcpServers:
  - name: filesystem
    command: $NPX
    args:
      - -y
      - "@modelcontextprotocol/server-filesystem"
      - $REPO_DIR
    env:
      PATH: "$NODE_BIN:/usr/bin:/bin"

  - name: git
    command: $VENV_DIR/bin/python
    args:
      - -m
      - mcp_server_git
      - --repository
      - $REPO_DIR
    env:
      PATH: "$GIT_BIN:/usr/bin:/bin"

  - name: github
    command: $NPX
    args:
      - -y
      - "@modelcontextprotocol/server-github"
    env:
      PATH: "$NODE_BIN:/usr/bin:/bin"
      GITHUB_PERSONAL_ACCESS_TOKEN: "$GITHUB_TOKEN"
EOF
  echo "  Written: $MCP_CONFIG"

  # ── Continue config ───────────────────────────────────────
  echo ""
  CONTINUE_CONFIG="$HOME/.continue/config.yaml"
  if [ ! -f "$CONTINUE_CONFIG" ]; then
    info "Copying Continue config to ~/.continue/config.yaml ..."
    mkdir -p "$HOME/.continue"
    cp "$REPO_DIR/config/continue/config.yaml" "$CONTINUE_CONFIG"
    echo "  Written: $CONTINUE_CONFIG"
  else
    info "~/.continue/config.yaml already exists — skipping."
    echo "  To overwrite: cp $REPO_DIR/config/continue/config.yaml $CONTINUE_CONFIG"
  fi

  # ── Docker stack ──────────────────────────────────────────
  echo ""
  info "Starting Docker stack..."
  cd "$REPO_DIR"
  docker compose down --remove-orphans 2>/dev/null || true

  info "Pulling images (first run may take a while)..."
  docker compose pull

  info "Starting services..."
  docker compose up -d

  # ── Wait for Ollama ───────────────────────────────────────
  echo ""
  info "Waiting for Ollama..."
  ATTEMPTS=0
  until curl -s http://localhost:11434 | grep -q "Ollama" 2>/dev/null; do
    ATTEMPTS=$((ATTEMPTS + 1))
    if [ $ATTEMPTS -gt 30 ]; then
      warn "Ollama not responding after 60s. Check: docker logs ollama"
      break
    fi
    echo -n "."
    sleep 2
  done
  echo ""

  # ── Summary ───────────────────────────────────────────────
  echo ""
  echo "============================================"
  info "Install complete!"
  echo "============================================"
  echo ""
  echo "Services:"
  echo "  Ollama API  : http://localhost:11434"
  echo "  Open WebUI  : http://localhost:3000"
  echo ""
  echo "Model pull progress:"
  echo "  docker logs -f ollama-init"
  echo ""
  echo "Continue.dev:"
  echo "  1. Install extension in VS Code"
  echo "  2. Ctrl+Shift+P -> Developer: Reload Window"
  echo ""
  echo "Useful commands:"
  echo "  docker compose ps"
  echo "  docker compose down"
  echo "  docker compose up -d"
  echo "  docker logs -f ollama"
  echo ""
}

case "$COMMAND" in
  install)   cmd_install ;;
  uninstall) cmd_uninstall ;;
  *)
    echo "Usage: $0 [install|uninstall]"
    exit 1
    ;;
esac
