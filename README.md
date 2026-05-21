# AlICS

Alice AI Coding Stack.

## Description

Local AI coding assistant. No cloud API keys. Runs entirely on your GPU.

| Component | Role |
|-----------|------|
| [Ollama](https://ollama.com) | Runs LLMs locally on your GPU |
| [Continue.dev](https://continue.dev) | VS Code AI assistant (chat, autocomplete, edit) |
| [Open WebUI](https://github.com/open-webui/open-webui) | Browser chat interface (optional) |
| MCP Servers | Give the AI access to your filesystem, git and GitHub |

## Requirements

- Linux (tested on Rocky Linux 9.4)
- NVIDIA GPU + drivers
- Python 3.11+
- Node.js 18+
- Git
- VS Code

## Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/yourorg/CodingStack.git
cd CodingStack
```

### 2. Run the install script

```bash
./install.sh
```

This will:
- Create a local `.venv/mcp` virtualenv
- Install MCP servers (filesystem, git, GitHub)
- Generate `.continue/mcpServers/default-mcp-server.yaml` with your local paths
- Copy the Continue config to `~/.continue/config.yaml`

### 3. Install Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Pull the default models (~14GB total):
```bash
ollama pull qwen2.5-coder:14b
ollama pull qwen2.5-coder:7b
```

### 4. Install Continue.dev in VS Code

Extensions → search **Continue** → Install

Or via CLI:
```bash
code --install-extension Continue.continue
```

### 5. Reload VS Code

`Ctrl+Shift+P` → `Developer: Reload Window`

The Continue sidebar should now show the AI chat with MCP tools active.

---

## Optional — Open WebUI (browser interface)

If you want a browser-based chat interface:

```bash
# Requires Docker + NVIDIA Container Toolkit
docker compose up -d
```

Then open http://localhost:3000

```bash
# Stop
docker compose down
```

See [Docker setup](#docker-setup) below if this is your first time.

---

## Daily Use

```bash
# Make sure Ollama is running
ollama serve          # if not running as a system service
curl http://localhost:11434   # should print "Ollama is running"
```

### VS Code Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+L` | Open chat panel |
| `Ctrl+I` | Inline edit selected code |
| `Tab` | Accept autocomplete suggestion |
| `Ctrl+Shift+L` | Add current file to chat context |

### What the AI can do with MCP

| Say this | What happens |
|----------|-------------|
| "Read auth.py and explain it" | AI reads the actual file |
| "Create branch feature/login and commit these changes" | AI runs git operations |
| "Open a PR for this branch" | AI uses GitHub API |
| "Fix the bug in the selected code" | AI edits inline |

---

## Changing Models

Edit `~/.continue/config.yaml` and change the model name.
Browse available models at https://ollama.com/library

```bash
# Pull a new model
ollama pull <model-name>

# List downloaded models
ollama list
```

---

## Docker Setup

Only needed if you want Open WebUI or don't want to install Ollama natively.

### Install Docker

```bash
sudo dnf config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo
sudo dnf -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl --now enable docker
sudo usermod -a -G docker $(whoami)
sudo reboot
```

### Install NVIDIA Container Toolkit

```bash
curl -s -L https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo | \
  sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo
sudo dnf install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Test
docker run --rm --gpus all nvidia/cuda:11.6.2-base-ubuntu20.04 nvidia-smi
```

---

## Troubleshooting

**Ollama not responding**
```bash
curl http://localhost:11434
sudo systemctl status ollama
sudo systemctl restart ollama
```

**MCP server not connecting**
```bash
# Re-run install to regenerate config with correct paths
./install.sh
# Then reload VS Code
```

**GPU not detected by Docker**
```bash
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

**Continue not picking up config**
```bash
ls ~/.continue/
# Should contain config.yaml
# Reload VS Code: Ctrl+Shift+P → Developer: Reload Window
```
