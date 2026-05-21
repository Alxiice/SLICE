# Install AlICS

## 0.Requirements

- docker
- nodejs
- have a github token

Add yourself in the docker group
```bash
sudo usermod -aG docker sonoleta
```

And now logout and log-in


## 1. Install continue extension

You need to install [continue](https://marketplace.visualstudio.com/items?itemName=Continue.continue)

> Extensions → search **Continue** → Install

On the settings, disable telemetry :

```json
{
    "continue.telemetryEnabled": false,
    "continue.showWelcomeTour": false,
    "continue.enableProxyServer": false,
    ...
}
```

## 2. Create the data directories

As we are going to install heavy files you might want to choose where they will be installed :
```bash
ROOT="/my/data/root"
sudo mkdir -p $ROOT/docker-data
sudo mkdir -p $ROOT/containerd-data
```

Update the following files to use these folders :
- config/docker/daemon.json
- config/docker/containerd.toml

Now set the docker config
```bash
sudo cp ./config/docker/daemon.json /etc/docker/daemon.json
sudo cp ./config/docker/containerd.toml /etc/containerd/config.toml
```

## 3. Start docker

```bash
sudo systemctl start docker
sudo systemctl restart containerd

```

Check :
```bash
docker ps   # should return empty list, no error
sudo systemctl status docker | head -5
```

## 4. Launch install script

First setup some environment variables :
```bash
export NODE_JS_PATH="/path/to/nodejs/version/bin"  # Contains npm, node, npx
export GITHUB_TOKEN="ghp_xxx"
```
Then :
```bash
./install.sh install
```

Now docker is going to fetch huge images. This will slow down your machine for a minute.
Follow the proogress with :
```bash
# Model download progress
docker logs -f ollama-init
# Open WebUI health
docker logs -f open-webui
```

## 5. Verfy everything runs

```bash
# 1. Check containers : you should get ollama and open-webui
docker compose ps
# 2. Check models were pulled
docker exec ollama ollama list
# 3. Check Ollama API responds
curl http://localhost:11434 && echo ""
```

## 6. Verify continue config

```bash
# Model config
cat ~/.continue/config.yaml  # Should be the same as config/continue/config.yaml

# MCP config
cat /s/apps/users/sonoleta/github/CodingStack/.continue/mcpServers/default-mcp-server.yaml
```
