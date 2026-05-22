# Install SLICE

## 0. Requirements

- Docker
- Node.js (with `npx` available)
- Python 3.11+
- Git
- VS Code
- A GitHub personal access token

Add yourself to the docker group and re-login:
```bash
sudo usermod -aG docker $USER
# logout and log back in
```

## 1. Install Continue extension

Install [Continue](https://marketplace.visualstudio.com/items?itemName=Continue.continue) in VS Code:

> Extensions → search **Continue** → Install

Or via CLI:
```bash
code --install-extension Continue.continue
```

Disable telemetry in VS Code settings (`settings.json`):
```json
{
    "continue.telemetryEnabled": false,
    "continue.showWelcomeTour": false,
    "continue.enableProxyServer": false
}
```

## 2. Create data directories

Ollama models and Open WebUI data can be large (~14GB+).
Choose where to store them:

```bash
ROOT="/my/data/root"
sudo mkdir -p $ROOT/docker-data
sudo mkdir -p $ROOT/containerd-data
```

Update the following files to point to these folders:
- `config/docker/daemon.json`
- `config/docker/containerd.toml`

Apply the Docker config:
```bash
sudo cp ./config/docker/daemon.json /etc/docker/daemon.json
sudo cp ./config/docker/containerd.toml /etc/containerd/config.toml
```

## 3. Start Docker

```bash
sudo systemctl start docker
sudo systemctl restart containerd
```

Check:
```bash
docker ps                                  # should return empty list, no error
sudo systemctl status docker | head -5
```

## 4. Run the install script

Set environment variables first:
```bash
export NODE_JS_PATH="/path/to/nodejs/bin"  # directory containing node, npm, npx
export GITHUB_TOKEN="ghp_xxx"
```

Then run:
```bash
./install.sh install
```

This will:
- Create `.venv/mcp` virtualenv and install `mcp-server-git`
- Generate `.mcp/run-filesystem.sh` and `.mcp/run-github.sh` wrapper scripts
- Generate `.continue/mcpServers/default-mcp-server.yaml` with your local paths
- Copy the Continue config to `~/.continue/config.yaml`
- Pull Docker images and start Ollama + Open WebUI

Docker will now fetch images and pull models (~14GB). This may take a while.

Follow progress:
```bash
docker logs -f ollama        # Ollama startup
docker logs -f open-webui    # Open WebUI health
```

Additionally : get nomic
```bash
docker exec ollama ollama pull nomic-embed-text
```

## 5. Verify everything runs

```bash
# 1. Check containers — should show ollama and open-webui
docker compose ps

# 2. Check models were pulled
docker exec ollama ollama list

# 3. Check Ollama API responds
curl http://localhost:11434 && echo ""

# 4. Open WebUI
# http://localhost:3000
```

## 6. Verify Continue config

```bash
# Model config
cat ~/.continue/config.yaml

# MCP wrapper scripts
ls -l .mcp/
```

Reload VS Code:
`Ctrl+Shift+P` → `Developer: Reload Window`

The Continue sidebar should now show the AI chat with MCP tools active.

## 7. Install another model

```bash
docker exec ollama ollama pull devstral-small-2
```

And then add this to the config file :

```bash
- name: Devstral Small 2
    provider: ollama
    model: devstral-small-2
    apiBase: http://localhost:11434
    contextLength: 16384      # keep this low to save VRAM for KV cache
    toolCallStrategy: auto
    systemMessage: >
      You are an expert coding assistant specializing in Python, QML, JavaScript,
      and C++. You work in a large VFX/animation pipeline codebase (Meshroom /
      AliceVision). Be concise. When editing, show only changed parts unless
      asked for the full file. Always use available tools (filesystem, git,
      github) rather than guessing — check before answering questions about
      code structure, current branch, file contents, or git history.
    roles:
      - chat
      - edit
      - apply
    capabilities:
      - tool_use
```

You can pre-load the model:
```bash
curl http://localhost:11434/api/generate -d '{"model": "devstral-small-2", "prompt": "", "keep_alive": -1}'
```
