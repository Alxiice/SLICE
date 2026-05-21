# SLICE

**S**elf-hosted **L**ocal **I**ntegrated **C**oding **E**nvironment

## Stack

| Component | Role |
|-----------|------|
| [Ollama](https://ollama.com) | Runs LLMs locally via Docker |
| [Continue.dev](https://continue.dev) | VS Code AI assistant (chat, autocomplete, edit) |
| [Open WebUI](https://github.com/open-webui/open-webui) | Browser chat interface |
| MCP Servers | Give the AI access to your filesystem, git and GitHub |

## Requirements

- Linux (tested on Rocky Linux 9.4)
- NVIDIA GPU + drivers
- Docker + NVIDIA Container Toolkit
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

### 2. Install

Follow the [Install](./INSTALL.md) file for detailed installation instructions.

---

## Services

| Service | URL |
|---------|-----|
| Ollama API | http://localhost:11434 |
| Open WebUI | http://localhost:3000 |

```bash
# Start
docker compose up -d

# Stop
docker compose down

# Status
docker compose ps
```

---

## Daily Use

```bash
# Check Ollama is running
curl http://localhost:11434 && echo ""   # should print "Ollama is running"

# Check models
docker exec ollama ollama list
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
docker exec ollama ollama pull <model-name>

# List downloaded models
docker exec ollama ollama list
```

---

## Docker Setup

### Install Docker

```bash
sudo dnf config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo
sudo dnf -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl --now enable docker
sudo usermod -aG docker $USER
# logout and log back in
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

## Uninstall

```bash
./install.sh uninstall
```

This will stop containers, remove volumes, images, virtualenv and generated configs.

---

## Troubleshooting

**Ollama not responding**
```bash
curl http://localhost:11434
docker logs ollama
docker compose restart ollama
```

**MCP server not connecting**
```bash
# Re-run install to regenerate wrapper scripts and config
./install.sh install

# Test wrapper scripts manually
.mcp/run-filesystem.sh
.mcp/run-github.sh

# Reload VS Code
# Ctrl+Shift+P → Developer: Reload Window
```

**GPU not detected by Docker**
```bash
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
docker run --rm --gpus all nvidia/cuda:11.6.2-base-ubuntu20.04 nvidia-smi
```

**Continue not picking up config**
```bash
ls ~/.continue/        # should contain config.yaml
ls .continue/mcpServers/   # should contain default-mcp-server.yaml
# Ctrl+Shift+P → Developer: Reload Window
```

**Models not available after install**
```bash
docker exec ollama ollama list
# If empty, pull manually:
docker exec ollama ollama pull qwen2.5-coder:14b
docker exec ollama ollama pull qwen2.5-coder:7b
