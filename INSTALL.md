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
