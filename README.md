# Multi-AI CLI OpenAI API Wrapper

> ⚠️ **WARNING: Active Refactoring in Progress**
> 
> This repository is currently undergoing significant refactoring and architectural changes. The codebase is **NOT STABLE** at this time. Features may be broken, APIs may change without notice, and documentation may not reflect the current state of the code.
> 
> **Use at your own risk.** We recommend waiting for the refactoring to complete before using this in production environments.

A unified OpenAI API-compatible endpoint for multiple AI CLIs, currently supporting **Anthropic Claude**, **Google Gemini**, and **Qwen Code**. The quickest and easiest way to leverage multiple AI providers through a single, standardized API interface.

## Attribution & History

This project began as a fork of the excellent [claude-code-openai-wrapper](https://github.com/RichardAtCT/claude-code-openai-wrapper) by RichardAtCT. Due to significant architectural changes and a shift in project focus toward simplified chat mode operations and multi-provider support, it has evolved into an independent repository. 

We are deeply grateful to the original author and contributors for their foundational work that made this project possible. The core infrastructure, Docker setup, and API compatibility layer build upon their excellent implementation.

## Project Goals

This wrapper is being simplified and optimized specifically for **chat mode operations**, making it the ideal solution for:

- **AI Coding Assistants** - Seamless integration with Roo Code, Cline, Cursor, and similar tools
- **Quick Multi-Provider Access** - Switch between Claude, Gemini, and Qwen without changing your code
- **Simplified Chat APIs** - Focus on chat completions without the complexity of file operations
- **Unified Endpoint** - One API to rule them all - no need to manage multiple SDKs or authentication methods

**Coming Soon**: Support for **Codex** CLI to expand multi-provider capabilities.

## Status

**Production Ready** - Optimized for AI coding assistants and chat applications:

### Multi-Provider Support
- **Anthropic Claude** - All Claude models via official SDK
- **Google Gemini** - Native CLI integration with all models
- **Qwen Code** - Full support for Qwen3-Coder models with thinking preservation
- **Codex** - [Planned]

### Core Features
- **Sandboxed execution** - Complete isolation for security
- **Web-based tools only** - Search and fetch capabilities
- **OpenAI-compatible API** - Drop-in replacement for any OpenAI client
- **Streaming support** - Real-time responses with progress indicators
- **Multimodal support** - Image analysis and processing
- **XML tool format support** - Compatible with Roo/Cline and similar tools

### Key Features
- **Automatic model routing** - Use `claude-*`, `gemini-*`, or `qwen-*` prefixes
- **Intelligent XML detection** - Confidence-based scoring avoids false positives
- **Advanced image support** - Model-specific injection strategies for optimal results
- **No API keys required** - Uses CLI authentication
- **Simple setup** - Get running in under 2 minutes
- **Docker support** - Easy deployment and scaling
- **Rate limiting** - Built-in protection against abuse

## Features

### Unified Multi-Provider API
- Single OpenAI-compatible endpoint for multiple AI providers
- Automatic model routing based on prefixes (`claude-*`, `gemini-*`)
- Drop-in replacement for OpenAI SDK - no code changes needed
- Support for streaming and non-streaming responses

### Optimized for Secure Chat APIs
- **Sandboxed execution** - Each request runs in isolation
- **No file system access** - Perfect for secure chat APIs
- **XML tool format support** - Compatible with AI coding assistants
- **Multimodal support** - Process images in various formats
- **Progress indicators** - Optional streaming feedback for users

### Simple Integration
- **No API keys required** - Uses CLI authentication
- **2-minute setup** - Clone, install, run
- **Full OpenAI SDK compatibility** - Works with any OpenAI client
- **Docker support** - Easy deployment and scaling
- **Rate limiting** - Built-in protection

## Quick Start

Get started in under 2 minutes:

### Prerequisites

- **Python 3.10+** - Required for the server
- **Poetry** - For dependency management
  ```bash
  curl -sSL https://install.python-poetry.org | python3 -
  ```

### Setup for Claude Code

```bash
# 1. Install Claude Code CLI (if not already installed)
npm install -g @anthropic-ai/claude-code

# 2. Authenticate (choose one method):
```

**Authentication Options:**
- **Option A**: Authenticate via CLI (Recommended for development)
  ```bash
  claude auth login
  ```
- **Option B**: Set environment variable
  ```bash
  export ANTHROPIC_API_KEY=your-api-key
  ```
- **Option C**: Use AWS Bedrock or Google Vertex AI (see Configuration section)

### Setup for Gemini

```bash
# 1. Install Gemini CLI
npm install -g @google/gemini-cli

# 2. Authenticate with Google account
gemini auth login
```

### Install and Run

```bash
# 1. Clone and setup the wrapper
git clone https://github.com/Labiri/clis-wrapper
cd clis-wrapper
poetry install

# 2. Start the server
poetry run uvicorn main:app --reload --port 8000

# 3. Test it works
poetry run python test_endpoints.py
```

**That's it!** Your OpenAI-compatible API is running on `http://localhost:8000`

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Labiri/clis-wrapper
   cd clis-wrapper
   ```

2. Install dependencies with Poetry:
   ```bash
   poetry install
   ```

   This will create a virtual environment and install all dependencies.

3. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your preferences
   ```

## Model Selection

The wrapper automatically routes requests based on the model name:

### Claude Models (prefix: `claude-*`)
- `claude-opus-4-1-20250805` - Most capable model (latest Opus 4.1)
- `claude-opus-4-20250514` - Claude Opus 4 - world's best coding model
- `claude-sonnet-4-20250514` - Claude Sonnet 4 - superior coding and reasoning
- `claude-3-7-sonnet-20250219` - Claude 3.7 Sonnet - hybrid reasoning model
- `claude-3-5-sonnet-20241022` - Previous generation Sonnet
- And all other Claude models available in your CLI

### Gemini Models (prefix: `gemini-*`)
- `gemini-2.5-pro` - Most advanced thinking model (default)
- `gemini-2.5-flash` - Fast, efficient model with thinking capabilities

### Progress Indicator Suffixes
Both Claude and Gemini models support progress indicator control:
- Standard mode (default) - No suffix needed, no progress markers
- `-progress` - Adds streaming progress indicators

Examples:
- `claude-opus-4-1-20250805` (standard mode)
- `claude-opus-4-1-20250805-progress` (with progress indicators)
- `gemini-2.5-flash-progress` (with progress indicators)

## Configuration

Edit the `.env` file:

```env
# Claude CLI Configuration
CLAUDE_CLI_PATH=claude

# Gemini CLI Configuration  
GEMINI_CLI_PATH=gemini
GEMINI_MODEL=gemini-2.5-pro  # Default model for Gemini

# API Configuration
# If API_KEY is not set, server will prompt for interactive API key protection on startup
# Leave commented out to enable interactive prompt, or uncomment to use a fixed API key
# API_KEY=your-optional-api-key-here
PORT=8000

# Timeout Configuration (milliseconds)
MAX_TIMEOUT=600000

# CORS Configuration
CORS_ORIGINS=["*"]

# Progress Indicator Configuration
# Progress indicators are controlled per-request by using model names with suffixes:
# Standard mode (default): No suffix needed (no progress markers)
# -progress: Adds streaming progress indicators
# Example: claude-opus-4-1-20250805-progress

# Session Cleanup
# Set to false to disable automatic Claude Code session cleanup
# When disabled, sessions will appear in Claude's /resume command
CLEANUP_SESSIONS=true

# Cleanup delay in minutes (default: 720 = 12 hours)
# Sessions are tracked and cleaned up after this delay
# Set to 0 for immediate cleanup after request completion
# Note: Claude Code tracks token usage per session. For accurate usage monitoring,
# sessions should persist long enough to capture complete usage data.
# 12 hours ensures sessions span daily usage boundaries for better tracking.
CLEANUP_DELAY_MINUTES=720

# SSE Keep-alive Configuration
# Interval in seconds between SSE keepalive comments to prevent connection timeouts
# These are invisible comments (lines starting with ':') that keep the connection alive
SSE_KEEPALIVE_INTERVAL=30

# Rate Limiting Configuration
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=30
RATE_LIMIT_CHAT_PER_MINUTE=10
RATE_LIMIT_DEBUG_PER_MINUTE=2
RATE_LIMIT_AUTH_PER_MINUTE=10
RATE_LIMIT_SESSION_PER_MINUTE=15
RATE_LIMIT_HEALTH_PER_MINUTE=30

# XML Detection Configuration
# Confidence threshold for XML detection (default: 5.0)
# Higher values = fewer false positives, lower values = more sensitive
# Range: 1.0-10.0, recommended: 5.0-7.0
XML_CONFIDENCE_THRESHOLD=5.0

# Known XML tools for detection (comma-separated list)
# These tool names will be detected in messages to trigger XML format enforcement
# Leave empty to disable tool-based detection
# Common tools for Roo/Cline: attempt_completion,ask_followup_question,read_file,write_to_file,run_command
XML_KNOWN_TOOLS=attempt_completion,ask_followup_question,read_file,write_to_file,run_command,str_replace_editor,search_files,list_files,new_task
```

### API Security Configuration

The server supports **interactive API key protection** for secure remote access:

1. **No API key set**: Server prompts "Enable API key protection? (y/N)" on startup
   - Choose **No** (default): Server runs without authentication
   - Choose **Yes**: Server generates and displays a secure API key

2. **Environment API key set**: Uses the configured `API_KEY` without prompting

```bash
# Example: Interactive protection enabled
poetry run python main.py

# Output:
# ============================================================
# API Endpoint Security Configuration
# ============================================================
# Would you like to protect your API endpoint with an API key?
# This adds a security layer when accessing your server remotely.
# 
# Enable API key protection? (y/N): y
# 
# 🔑 API Key Generated!
# ============================================================
# API Key: Xf8k2mN9-vLp3qR5_zA7bW1cE4dY6sT0uI
# ============================================================
# 📋 IMPORTANT: Save this key - you'll need it for API calls!
#    Example usage:
#    curl -H "Authorization: Bearer Xf8k2mN9-vLp3qR5_zA7bW1cE4dY6sT0uI" \
#         http://localhost:8000/v1/models
# ============================================================
```

**Perfect for:**
- 🏠 **Local development** - No authentication needed
- 🌐 **Remote access** - Secure with generated tokens
- **VPN/Tailscale** - Add security layer for remote endpoints

### Progress Markers

Control streaming progress indicators through model name suffixes:

- **Without progress markers** (default - no suffix needed)
  - **IMPORTANT**: Only streams the final assistant response - all intermediate content is filtered out

- **With progress markers** (`model-name-progress`)
  - Shows initial hourglass (⏳) followed by rotating circles (◐ ◓ ◑ ◒) with dots
  - Uses exponential backoff to avoid being too chatty
  - Perfect for user-facing applications where visual feedback is important
  - Completely removes:
    - Tool use messages and results
    - Intermediate reasoning steps
    - Multiple assistant messages (only the final one is sent)
    - Any SDK internal messages
  - Waits for Claude to complete all processing before streaming begins
  - SSE keepalives are sent every `SSE_KEEPALIVE_INTERVAL` seconds during SDK buffering
  - Ideal for programmatic usage when you need clean, final responses only
  - Note: Higher initial latency due to buffering, but cleaner output

### 🔄 **SSE Keepalive Configuration**

Prevents connection timeouts during long-running requests by sending invisible keepalive comments:

- **Default interval**: 30 seconds (`SSE_KEEPALIVE_INTERVAL=30`)
- **How it works**: Sends SSE comments (lines starting with `:`) that are automatically ignored by clients
- **When it's used**: During any pause in streaming longer than the configured interval
- **Invisible to clients**: Keepalive comments don't appear in the response content

This feature ensures that:
- Long Claude processing times don't cause connection timeouts
- Proxies and load balancers don't close "idle" connections
- Works identically in both progress marker modes:
  - With progress markers: Keepalives sent between progress updates
  - Without progress markers: Keepalives sent during SDK response buffering
- Connections remain active even when the SDK takes time to respond

The progress indicators use universal, language-agnostic symbols:
- Starts with ⏳ (hourglass) to indicate processing has begun
- Transitions to rotating circles (◐ ◓ ◑ ◒) for ongoing progress
- Adds dots (·) incrementally to show continued activity
- Example progression: ⏳ → ⏳· → ◐ → ◐· → ◐·· → ◓ → ◓·

### Rate Limiting

Built-in rate limiting protects against abuse and ensures fair usage:

- **Chat Completions** (`/v1/chat/completions`): 10 requests/minute
- **Debug Requests** (`/v1/debug/request`): 2 requests/minute
- **Auth Status** (`/v1/auth/status`): 10 requests/minute
- **Health Check** (`/health`): 30 requests/minute

Rate limits are applied per IP address using a fixed window algorithm. When exceeded, the API returns HTTP 429 with a structured error response:

```json
{
  "error": {
    "message": "Rate limit exceeded. Try again in 60 seconds.",
    "type": "rate_limit_exceeded",
    "code": "too_many_requests",
    "retry_after": 60
  }
}
```

Configure rate limiting through environment variables:

```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_CHAT_PER_MINUTE=10
RATE_LIMIT_DEBUG_PER_MINUTE=2
RATE_LIMIT_AUTH_PER_MINUTE=10
RATE_LIMIT_HEALTH_PER_MINUTE=30
```

## Running the Server

1. Verify Claude Code is installed and working:
   ```bash
   claude --version
   claude --print --model claude-3-5-haiku-20241022 "Hello"  # Test with fast model
   ```

2. Start the server:

   **Development mode (recommended - auto-reloads on changes):**
   ```bash
   poetry run uvicorn main:app --reload --port 8000
   ```

   **Production mode:**
   ```bash
   poetry run python main.py
   ```

   **Port Options for production mode:**
   - Default: Uses port 8000 (or PORT from .env)
   - If port is in use, automatically finds next available port
   - Specify custom port: `poetry run python main.py 9000`
   - Set in environment: `PORT=9000 poetry run python main.py`

## Docker Setup Guide

This guide provides a comprehensive overview of building, running, and configuring a Docker container for the Multi-AI CLI OpenAI Wrapper. Docker enables isolated, portable, and reproducible deployments of the wrapper, which acts as an OpenAI-compatible API server routing requests to both Anthropic's Claude models and Google's Gemini models. This setup supports authentication methods like Claude subscriptions (e.g., Max plan via OAuth for fixed-cost quotas), direct API keys, AWS Bedrock, Google Vertex AI, and Gemini CLI authentication.

By containerizing the application, you can run it locally for development, deploy it to remote servers or cloud platforms, and customize behavior through environment variables and volumes. This guide assumes you have already cloned the repository and have the `Dockerfile` in the root directory. For general repository setup (e.g., Claude Code CLI authentication), refer to the sections above.

## Prerequisites
Before building or running the container, ensure the following:
- **Docker Installed**: Docker Desktop (for macOS/Windows) or Docker Engine (for Linux). Verify with `docker --version` (version 20+ recommended). Test basic functionality with `docker run hello-world`.
- **Claude Authentication Configured**: For subscription-based access (e.g., Claude Max), ensure the Claude Code CLI is authenticated on your host machine, with tokens in `~/.claude/`. This directory will be mounted into the container. Refer to the Prerequisites section above for CLI setup if needed.
- **Hardware and Software**:
  - OS: macOS (10.15+), Linux (e.g., Ubuntu 20.04+), or Windows (10+ with WSL2 for optimal volume mounting).
  - Resources: At least 4GB RAM and 2 CPU cores (Claude requests can be compute-intensive; monitor with `docker stats`).
  - Disk: ~500MB for the image, plus space for volumes.
  - Network: Stable internet for builds (dependency downloads) and runtime (API calls to Anthropic).
- **Optional**:
  - Docker Compose: For multi-service or easier configuration management. Install via Docker Desktop or your package manager (e.g., `sudo apt install docker-compose`).
  - Tools for Remote Deployment: Access to a VPS (e.g., AWS EC2, DigitalOcean), cloud registry (e.g., Docker Hub), or platform (e.g., Heroku, Google Cloud Run) if planning remote use.

## Building the Docker Image
The `Dockerfile` in the root defines a lightweight Python 3.12-based image with all dependencies (Poetry, Node.js for CLI, FastAPI/Uvicorn, and the Claude Code SDK).

1. Navigate to the repository root (where the Dockerfile is).
2. Build the image:
   ```bash
   docker build -t claude-wrapper:latest .
   ```
   - `-t claude-wrapper:latest`: Tags the image (replace `:latest` with a version like `:v1.0` for production).
   - `.`: Builds from the current directory context.
   - Build Time: 5-15 minutes on first run (subsequent builds cache layers).
   - Size: Approximately 200-300MB.

3. Verify the Build:
   ```bash
   docker images | grep claude-wrapper
   ```
   This lists the image with its tag and size.

4. Advanced Build Options:
   - No Cache (for fresh builds): `docker build --no-cache -t claude-wrapper:latest .`.
   - Platform-Specific (e.g., ARM for Raspberry Pi): `docker build --platform linux/arm64 -t claude-wrapper:arm .`.
   - Multi-Stage for Smaller Size: If optimizing, modify the Dockerfile to use multi-stage builds (e.g., separate build and runtime stages).

If using Docker Compose (see below), build with `docker-compose build`.

## Running the Container Locally
Once built, run the container to start the API server. The default port is 8000, and the API is accessible at `http://localhost:8000/v1` (e.g., `/v1/chat/completions` for requests).

### Basic Production Run
For stable, background operation:
```bash
docker run -d -p 8000:8000 \
  -v ~/.claude:/root/.claude \
  -v ~/.claude-wrapper:/root/.claude-wrapper \
  --name claude-wrapper-container \
  claude-wrapper:latest
```
- `-d`: Detached mode (runs in background).
- `-p 8000:8000`: Maps host port 8000 to the container's 8000 (change left side for host conflicts, e.g., `-p 9000:8000`).
- `-v ~/.claude:/root/.claude`: Mounts your host's authentication directory for persistent subscription tokens (essential for Claude Max access).
- `-v ~/.claude-wrapper:/root/.claude-wrapper`: Mounts session tracking directory for chat mode cleanup functionality.
- `--name claude-wrapper-container`: Names the container for easy management.

### Development Run with Hot Reload
For coding/debugging (auto-reloads on file changes):
```bash
docker run -d -p 8000:8000 \
  -v ~/.claude:/root/.claude \
  -v ~/.claude-wrapper:/root/.claude-wrapper \
  -v $(pwd):/app \
  --name claude-wrapper-container \
  claude-wrapper:latest \
  poetry run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
- `-v $(pwd):/app`: Mounts the current directory (repo root) into the container for live code edits.
- Command Override: Uses Uvicorn with `--reload` for development.

### Using Docker Compose for Simplified Runs
Create or use an existing `docker-compose.yml` in the root for declarative configuration:
```yaml
version: '3'
services:
  claude-wrapper:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ~/.claude:/root/.claude
      - ~/.claude-wrapper:/root/.claude-wrapper  # For session tracking
      # - .:/app  # Optional for dev - uncomment to mount code for hot reload
    environment:
      # Claude CLI Configuration
      - CLAUDE_CLI_PATH=${CLAUDE_CLI_PATH:-claude}
      # Gemini CLI Configuration
      - GEMINI_CLI_PATH=${GEMINI_CLI_PATH:-gemini}
      - GEMINI_MODEL=${GEMINI_MODEL:-gemini-2.5-pro}
      # API Configuration
      - PORT=${PORT:-8000}
      - API_KEY=${API_KEY:-}
      # Timeout Configuration
      - MAX_TIMEOUT=${MAX_TIMEOUT:-600000}
      # CORS Configuration
      - CORS_ORIGINS=${CORS_ORIGINS:-["*"]}
      # Logging Configuration
      - DEBUG_MODE=${DEBUG_MODE:-false}
      - VERBOSE=${VERBOSE:-false}
      # Session Cleanup Configuration
      - CLEANUP_SESSIONS=${CLEANUP_SESSIONS:-true}
      - CLEANUP_DELAY_MINUTES=${CLEANUP_DELAY_MINUTES:-720}
      # SSE Keep-alive
      - SSE_KEEPALIVE_INTERVAL=${SSE_KEEPALIVE_INTERVAL:-30}
      # XML Detection Configuration
      - XML_CONFIDENCE_THRESHOLD=${XML_CONFIDENCE_THRESHOLD:-5.0}
      - XML_KNOWN_TOOLS=${XML_KNOWN_TOOLS:-attempt_completion,ask_followup_question,read_file,write_to_file,run_command,str_replace_editor,search_files,list_files,new_task,apply_diff,execute_command,switch_mode,update_todo_list}
      # Rate Limiting Configuration
      - RATE_LIMIT_ENABLED=${RATE_LIMIT_ENABLED:-true}
      - RATE_LIMIT_PER_MINUTE=${RATE_LIMIT_PER_MINUTE:-30}
      - RATE_LIMIT_CHAT_PER_MINUTE=${RATE_LIMIT_CHAT_PER_MINUTE:-10}
      - RATE_LIMIT_DEBUG_PER_MINUTE=${RATE_LIMIT_DEBUG_PER_MINUTE:-2}
      - RATE_LIMIT_AUTH_PER_MINUTE=${RATE_LIMIT_AUTH_PER_MINUTE:-10}
      - RATE_LIMIT_SESSION_PER_MINUTE=${RATE_LIMIT_SESSION_PER_MINUTE:-15}
      - RATE_LIMIT_HEALTH_PER_MINUTE=${RATE_LIMIT_HEALTH_PER_MINUTE:-30}
    # Production mode example - uncomment the line below to run without hot reload
    # command: ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
    # Note: The default Dockerfile CMD includes --reload for development mode
    restart: unless-stopped
```
- Run: `docker-compose up -d` (builds if needed, runs detached).
- Stop: `docker-compose down`.

### Post-Run Management
- View Logs: `docker logs claude-wrapper-container` (add `-f` for real-time tailing).
- Check Status: `docker ps` (lists running containers) or `docker stats` (resource usage).
- Stop/Restart: `docker stop claude-wrapper-container` and `docker start claude-wrapper-container`.
- Remove: `docker rm claude-wrapper-container` (after stopping; use `-f` to force).
- Cleanup: `docker system prune` to remove unused images/volumes.

## Custom Configuration Options
Customize the container's behavior through environment variables, volumes, and runtime flags. Most changes don't require rebuilding—just restart the container.

### Environment Variables
Env vars override defaults and can be set at runtime with `-e` flags or in `docker-compose.yml` under `environment`. They control auth, server settings, and SDK behavior.

- **Claude Configuration**:
  - `CLAUDE_CLI_PATH=claude`: Path to Claude CLI executable (default: claude).

- **Gemini Configuration**:
  - `GEMINI_CLI_PATH=gemini`: Path to Gemini CLI executable (default: gemini).
  - `GEMINI_MODEL=gemini-2.5-pro`: Default Gemini model (default: gemini-2.5-pro).

- **General Configuration**:
  - `DEBUG_MODE=false`: Enable debug logging (default: false).
  - `VERBOSE=false`: Enable verbose logging (default: false).
  - `SHOW_PROGRESS_MARKERS=true`: Show progress indicators during streaming (default: true).
  - `PROGRESS_STYLE=text`: Progress indicator style: text, spinner, ascii, minimal (default: text).
  - `CLEANUP_SESSIONS=true`: Cleanup provider sessions after requests (default: true).
  - `CLEANUP_DELAY_MINUTES=720`: Minutes to wait before cleanup (default: 720 = 12 hours).
  - `API_KEY`: API key for endpoint protection (leave unset for interactive prompt).
  - `PORT=8000`: Server port (default: 8000).
  - `CORS_ORIGINS=["*"]`: Allowed CORS origins (default: ["*"]).
  - `MAX_TIMEOUT=600000`: Maximum request timeout in ms (default: 600000).

- **SSE Configuration**:
  - `SSE_KEEPALIVE_INTERVAL=30`: Interval in seconds for sending SSE keepalive comments (default: 30).

- **XML Detection Configuration**:
  - `XML_CONFIDENCE_THRESHOLD=5.0`: Confidence threshold for XML detection (default: 5.0).
  - `XML_KNOWN_TOOLS`: Known XML tools for detection (comma-separated list).

- **Rate Limiting Configuration**:
  - `RATE_LIMIT_ENABLED=true`: Enable rate limiting for all endpoints (default: true).
  - `RATE_LIMIT_PER_MINUTE=30`: General rate limit per minute (default: 30).
  - `RATE_LIMIT_CHAT_PER_MINUTE=10`: Chat completions rate limit per minute (default: 10).
  - `RATE_LIMIT_DEBUG_PER_MINUTE=2`: Debug endpoint rate limit per minute (default: 2).
  - `RATE_LIMIT_AUTH_PER_MINUTE=10`: Auth endpoint rate limit per minute (default: 10).
  - `RATE_LIMIT_SESSION_PER_MINUTE=15`: Session endpoint rate limit per minute (default: 15).
  - `RATE_LIMIT_HEALTH_PER_MINUTE=30`: Health check rate limit per minute (default: 30).

- **Authentication and Providers**:
  - `ANTHROPIC_API_KEY=sk-your-key`: Enables direct API key auth (generate at console.anthropic.com).
  - `CLAUDE_CODE_USE_VERTEX=true`: Switches to Google Vertex AI (requires additional configuration).
  - `CLAUDE_CODE_USE_BEDROCK=true`: Enables AWS Bedrock (requires AWS credentials).

Example with Env Vars:
```bash
docker run ... -e PORT=9000 -e ANTHROPIC_API_KEY=sk-your-key ...
```

For persistence across runs, use a `.env` file in the root (e.g., `PORT=8000`) and mount it: `-v $(pwd)/.env:/app/.env`. Load vars in code if required.

### Volumes for Data Persistence and Customization
Volumes mount host directories/files into the container, enabling persistence and config overrides.

- **Authentication Volume (Required for Subscriptions)**: `-v ~/.claude:/root/.claude` – Shares tokens and `settings.json` (edit on host for defaults like `"max_tokens": 8192`; restart container to apply).
- **Session Tracking Volume**: `-v ~/.claude-wrapper:/root/.claude-wrapper` – Stores session tracking data for chat mode cleanup functionality.
- **Code Volume (Dev Only)**: `-v $(pwd):/app` – Allows live edits without rebuilds.
- **Custom Config Volumes**: 
  - Mount a custom config: `-v /path/to/custom.json:/app/config/custom.json` (load in code).
  - Logs: `-v /path/to/logs:/app/logs` for external log access.
- **Credential Files**: For Vertex/Bedrock, `-v /path/to/creds.json:/app/creds.json` and set env var to point to it.

Volumes survive container restarts but are deleted on `docker rm -v`. Use named volumes for better management (e.g., `docker volume create claude-auth` and `-v claude-auth:/root/.claude`).

### Runtime Flags and Overrides
- Resource Limits: `--cpus=2 --memory=2g` to cap CPU/RAM (prevent overconsumption).
- Network: `--network host` for host networking (useful for local integrations).
- Restart Policy: `--restart unless-stopped` for auto-recovery on crashes.
- User: `--user $(id -u):$(id -g)` to run as your host user (avoid root permissions).

Per-request configs (e.g., `max_tokens`, `model`) are handled in API payloads, not container flags.

## Using the Container Remotely
For remote access (e.g., from other machines or production deployment), extend the local setup.

### Exposing Locally for Remote Access
- Bind to All Interfaces: Already done with `--host 0.0.0.0`.
- Firewall: Open port 8000 on your host (e.g., `ufw allow 8000` on Ubuntu).
- Tunneling: Use ngrok for temporary exposure: Install ngrok, run `ngrok http 8000`, and use the public URL.
- Security: Always add `API_KEYS` and use HTTPS (via reverse proxy).

### Deploying to a Remote Server or VPS
1. Push Image to Registry: 
   ```bash
   docker tag claude-wrapper:latest yourusername/claude-wrapper:latest
   docker push yourusername/claude-wrapper:latest
   ```
   (Create a Docker Hub account if needed.)

2. On Remote Server (e.g., AWS EC2, DigitalOcean Droplet):
   - Install Docker.
   - Pull Image: `docker pull yourusername/claude-wrapper:latest`.
   - Run: Use the production command above, but copy `~/.claude/` to the server first (e.g., via scp) or re-auth CLI remotely.
   - Persistent Storage: Use server volumes (e.g., `-v /server/path/to/claude:/root/.claude`).
   - Background: Use systemd or screen for daemonization.

3. Cloud Platforms:
   - **Heroku**: Use `heroku container:push web` after installing Heroku CLI; set env vars in dashboard.
   - **Google Cloud Run**: `gcloud run deploy --image yourusername/claude-wrapper --port 8000 --allow-unauthenticated`.
   - **AWS ECS**: Create a task definition with the image, set env vars, and deploy as a service.
   - Scaling: Platforms like Kubernetes can auto-scale based on load.

4. HTTPS and Security for Remote:
   - Use a Reverse Proxy: Add Nginx/Apache in another container (e.g., via Compose) with SSL (Let's Encrypt).
   - Example Nginx Config (mount as volume): Redirect HTTP to HTTPS, proxy to 8000.
   - Monitoring: Integrate CloudWatch/Prometheus for logs/metrics.

Remote usage respects your Claude quotas (shared across instances). For high availability, use load balancers.

## Testing the Container
Validate setup post-run:
1. Health Check: `curl http://localhost:8000/health` (expect `{"status": "healthy"}`).
2. Models List: `curl http://localhost:8000/v1/models`.
3. Completion Request: 
   ```bash
   curl http://localhost:8000/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model": "claude-opus-4-1-20250805", "messages": [{"role": "user", "content": "Hello"}]}'
   ```
4. Tool/Subscription Test: Send multiple requests; check logs for auth mode.
5. Remote Test: From another machine, curl the server's IP/port.

Use `test_endpoints.py` from the repo (mount code and run inside container: `docker exec claude-wrapper-container poetry run python test_endpoints.py`).

## Troubleshooting
- **Build Fails**: Check Dockerfile syntax; clear cache (`--no-cache`); ensure internet.
- **Run Errors**:
  - Auth: Verify `~/.claude` mount; re-auth CLI.
  - Port in Use: Change mapping or kill processes (`lsof -i:8000`).
  - Dep Issues: Rebuild; check Poetry lock file.
- **Remote Access Problems**: Firewall rules, DNS, or use `--network host`.
- **Performance**: Increase resources (`--cpus`); switch models.
- **Logs/Debug**: `docker logs -f claude-wrapper-container`; enter shell `docker exec -it claude-wrapper-container /bin/bash`.
- **Cleanup**: `docker system prune -a` for full reset.

Report issues on GitHub with logs/image tag/OS details.

## Usage Examples

### Using curl

```bash
# Claude model
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-opus-4-1-20250805",
    "messages": [
      {"role": "user", "content": "What is 2 + 2?"}
    ]
  }'

# Gemini model
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.5-flash",
    "messages": [
      {"role": "user", "content": "What is 2 + 2?"}
    ]
  }'

# With API key protection (when enabled)
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-generated-api-key" \
  -d '{
    "model": "claude-sonnet-4-20250514",
    "messages": [
      {"role": "user", "content": "Write a Python hello world script"}
    ],
    "stream": true
  }'
```

### Using OpenAI Python SDK

```python
from openai import OpenAI

# Configure client (automatically detects auth requirements)
client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="your-api-key-if-required"  # Only needed if protection enabled
)

# Alternative: Let examples auto-detect authentication
# The wrapper's example files automatically check server auth status

# Using Claude model
response = client.chat.completions.create(
    model="claude-opus-4-1-20250805",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What files are in the current directory?"}
    ]
)

print(response.choices[0].message.content)

# Using Gemini model
response = client.chat.completions.create(
    model="gemini-2.5-pro",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain quantum computing in simple terms."}
    ]
)

print(response.choices[0].message.content)
# Output: Fast response with secure web-based tools only

# Check real costs and tokens
print(f"Cost: ${response.usage.total_tokens * 0.000003:.6f}")  # Real cost tracking
print(f"Tokens: {response.usage.total_tokens} ({response.usage.prompt_tokens} + {response.usage.completion_tokens})")

# Streaming with progress indicators
stream = client.chat.completions.create(
    model="claude-sonnet-4-20250514-progress",
    messages=[
        {"role": "user", "content": "Explain quantum computing"}
    ],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

## Supported Models

The wrapper dynamically discovers available models from the Claude and Gemini CLIs at startup. Models are automatically extracted and cached for 24 hours.

### Claude Models (auto-discovered):
- `claude-opus-4-1-20250805` - Most capable model (Opus 4.1, August 2025)
- `claude-opus-4-20250514` - World's best coding model (May 2025)
- `claude-sonnet-4-20250514` - Superior coding and reasoning (May 2025)
- `claude-3-7-sonnet-20250219` - Hybrid reasoning model (February 2025)
- `claude-3-5-sonnet-20241022` - Previous generation
- `claude-3-5-haiku-20241022` - Fast, efficient model

### Gemini Models:
- `gemini-2.5-pro` - Most advanced thinking model (default)
- `gemini-2.5-flash` - Fast model with thinking capabilities

The model parameter is passed directly to the appropriate CLI. Each model also supports:
- Standard mode (default) - No suffix needed
- `{model}-progress` - With streaming progress indicators

View all available models and their variants:
```bash
curl http://localhost:8000/v1/models
```

## Web Search Capabilities

Both Claude and Gemini models have built-in web search functionality:

- **Claude Models**: Web search via WebSearch and WebFetch tools (enabled in chat mode)
- **Gemini Models**: Native web search capability built into the Gemini CLI

This allows both models to:
- Search for current information and events
- Fetch content from web pages
- Access real-time data (weather, stock prices, etc.)
- Research topics beyond their training data cutoff

Note: Web search works automatically - just ask questions that require current information!

## Conversation Management

The wrapper operates in a **stateless mode** where each request is independent, just like the standard OpenAI API. For conversation continuity, clients should manage conversation state by including the full conversation history in each request's messages array.

## Secure Chat API

The wrapper provides a secure **sandboxed chat API** that transforms Claude Code into a chat-only AI with no file system access. This design ensures complete security isolation while providing powerful AI capabilities.

### Security Features

The wrapper operates with these security constraints:

```bash
# Standard operation (secure by default)
curl -X POST http://localhost:8000/v1/chat/completions \
  -d '{"model": "claude-3-5-sonnet-20241022", ...}'

# With progress markers for user-friendly feedback
curl -X POST http://localhost:8000/v1/chat/completions \
  -d '{"model": "claude-3-5-sonnet-20241022-chat-progress", ...}'
```

### Security Properties

- **No File System Access**: All file operations are completely blocked
- **Limited Tools**: Only WebSearch and WebFetch tools are available
- **Sandboxed Execution**: Each request runs in an isolated temporary directory
- **Stateless Operation**: No persistent sessions (clients manage conversation state)
- **Format Support**: Automatic detection and support for XML tool formats and JSON responses
- **Prompt Engineering**: Multiple system prompts ensure secure chat-only behavior
- **Automatic Cleanup**: Temporary files are automatically removed after each request

### Complete Security Isolation

- **Stateless Operation**: Each request is independent and runs in a fresh sandbox
- **Path Hiding**: Environment variables that could reveal system paths are removed
- **Tool Restrictions**: Only web-based tools allowed, no local system access
- **Automatic Cleanup**: Temporary sandbox directories are cleaned immediately; Claude Code session files are cleaned based on configured delay
- **Time-Based Cleanup**: Sessions are tracked and cleaned after a delay (default: 12 hours for complete usage tracking)
- **No Persistence**: Sessions are removed after the delay period (configurable via `CLEANUP_SESSIONS` and `CLEANUP_DELAY_MINUTES`)

### Important Notes

- **Stateless Design**: Clients should handle their own conversation continuity
- **No File Persistence**: Nothing is saved between requests
- **Web Tools Only**: Only WebSearch and WebFetch tools are available

### Session Cleanup Configuration

The wrapper provides flexible session cleanup options:

- **`CLEANUP_SESSIONS`**: Master on/off switch for session cleanup (default: `true`)
- **`CLEANUP_DELAY_MINUTES`**: Minutes to wait before cleanup (default: `720` = 12 hours)
  - Set to `0` for immediate cleanup after request completion
  - Sessions are tracked and cleaned up by a background task
  - On startup, old sessions exceeding the delay are automatically cleaned

### Token Usage Tracking and Monitoring

Claude Code tracks token usage at the session level. Each session file contains the complete token consumption data for all requests within that session. This has important implications for usage monitoring:

- **Token Usage Aggregation**: Claude Code aggregates token usage per session, not per request
- **Daily Usage Tracking**: For accurate daily token consumption reports, sessions should persist across usage periods
- **12-Hour Default**: The 12-hour delay ensures sessions span daily usage boundaries, capturing complete usage patterns
- **Monitoring Tools**: Usage tracking dashboards and cost analysis tools need access to session files to calculate token consumption

### Monitoring Considerations

- **With delayed cleanup** (default 12 hours): Sessions remain available long enough for monitoring tools to capture complete daily usage data
- **Immediate cleanup** (`CHAT_MODE_CLEANUP_DELAY_MINUTES=0`): May result in incomplete usage statistics as sessions are deleted before aggregation
- **To preserve logs indefinitely**: Set `CHAT_MODE_CLEANUP_SESSIONS=false` - sessions accumulate but provide complete historical data
- **Recommended for monitoring**: Use at least 12-24 hours delay to ensure usage data spans daily boundaries

### Important Note on Existing Sessions

**Currently, sessions created while `CLEANUP_SESSIONS=false` will NOT be automatically cleaned up when switching to `CLEANUP_SESSIONS=true`.** Only new sessions created after enabling cleanup will be tracked and cleaned. To manually clean old sessions, you'll need to delete them from `~/.claude/projects/` directories containing "claude-chat-sandbox" in their names.

### Example Usage

```python
# Example showing dynamic mode selection per request
import openai

client = openai.OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="your-api-key"
)

# Standard secure operation
response = client.chat.completions.create(
    model="claude-opus-4-1-20250805",
    messages=[{"role": "user", "content": "Explain quantum computing"}]
)

# With progress markers for user feedback
response = client.chat.completions.create(
    model="claude-opus-4-1-20250805-progress",
    messages=[{"role": "user", "content": "Explain quantum computing"}]
)

# Simple chat request - runs in complete isolation
response = client.chat.completions.create(
    model="claude-sonnet-4-20250514",
    messages=[
        {"role": "user", "content": "Write a Python function to calculate fibonacci numbers"}
    ]
)
# Claude will output the code in markdown blocks, cannot create files

# XML tool format automatically detected and supported
response = client.chat.completions.create(
    model="gemini-2.5-pro",
    messages=[
        {"role": "system", "content": "Tool uses are formatted using XML-style tags..."},
        {"role": "user", "content": "Search for information about Python asyncio"}
    ]
)
# The model will use the XML format if provided by the client
```

### Secure Design

| Feature | Status |
|---------|---------|
| File Operations | Blocked |
| System Commands | Blocked |
| Web Tools | Claude: WebSearch, WebFetch; Gemini: Native web search |
| Sessions | Disabled (stateless) |
| Working Directory | Temporary sandbox |
| Environment | Sanitized environment |

### Use Cases

Chat mode is ideal for:
- **AI Coding Assistants**: Integration with tools like Roo Code, Cline, Cursor, and other AI coding assistants that expect OpenAI-compatible APIs
- **Public APIs**: Safely expose Claude as a chat service
- **Chat Applications**: Integration with chat clients that manage their own state
- **Restricted Environments**: When you need Claude's capabilities without system access
- **Multi-tenant Services**: Ensure complete isolation between requests
- **Development Tools**: IDEs and extensions that need AI assistance without file system access

## Multimodal Image Support

The wrapper provides comprehensive image support with model-specific optimization, handling both OpenAI-format images and file-based references commonly used by AI coding assistants.

### Supported Image Formats

1. **OpenAI Format** - Standard multimodal messages:
   ```json
   {
     "role": "user",
     "content": [
       {"type": "text", "text": "What's in this image?"},
       {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
     ]
   }
   ```

2. **File-Based References** - Used by Roo/Cline and similar tools:
   ```json
   {
     "role": "user",
     "content": "Analyze this image:\n[Image #1]"
   }
   ```

### Intelligent Image Processing

The wrapper uses **message boundary detection** to intelligently process only new images:

- **First Message**: Processes all images when no assistant response exists yet
- **Conversation History**: Identifies messages after the last assistant response as "new"
- **Avoids Reprocessing**: Historical images from previous turns are not re-analyzed
- **Stateless Operation**: Works within ephemeral sandbox constraints

### How It Works

1. **Image Detection**: Automatically detects images in messages (both formats)
2. **Smart Processing**: Uses message flow analysis to identify new vs. historical images
3. **Model-Specific Injection**: 
   - **Claude**: Always uses inline injection for proven reliability
   - **Gemini**: 
     - Uses sandbox mode (`-s` flag) for reliable file access
     - Includes file validation before processing
     - Implements retry logic for transient failures  
     - Extracts relevant details for contextual questions rather than attempting direct answers
     - System messages for XML scenarios, inline otherwise
4. **Isolated Analysis**: Each model processes images via isolated CLI calls
5. **Sandbox Saving**: Saves images to temporary sandbox directory
6. **Context Integration**: Analysis results injected into conversation context
7. **Path Mapping**: Maps placeholders like `[Image #1]` to actual file paths

### Technical Details

- **Maximum Images**: 20 per request
- **Size Limit**: 3.75 MB per image
- **Supported Types**: PNG, JPEG, GIF, WebP, BMP, TIFF
- **Processing**: Base64 decoding, URL downloading, caching to avoid duplicates
- **Sandbox Isolation**: Each request gets a fresh sandbox in chat mode

### Example Usage

```python
import openai

client = openai.OpenAI(base_url="http://localhost:8000/v1", api_key="dummy")

# Send an image for analysis
response = client.chat.completions.create(
    model="claude-opus-4-1-20250805",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "What's in this image?"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
        ]
    }]
)
```

## Intelligent XML Tool Format Detection

The wrapper includes sophisticated XML format detection that works intelligently with any AI assistant (Roo, Cline, Cursor, etc.) while avoiding false positives from code discussions.

### How It Works

The system uses **confidence-based scoring** to determine when XML tool format is required:

- **High Confidence Indicators** (3 points each):
  - Mandatory tool usage directives
  - XML format specifications
  - Tool name definitions (`<tool_name>...</tool_name>`)
  - Specific tool response formats

- **Medium Confidence Indicators** (2 points each):
  - Known tool names (`attempt_completion`, `ask_followup_question`)
  - Tool usage instructions
  - Tool list headers

- **Low Confidence Indicators** (1 point each):
  - Compound XML tags
  - Tool/XML keyword mentions

- **Negative Indicators** (subtract points):
  - File extensions (.xml, .html)
  - Code discussions about XML
  - Example contexts

### Smart Features

1. **Code Block Stripping**: Automatically removes code blocks before analysis to prevent false positives
2. **System Message Bonus**: Gives extra weight to system message instructions
3. **Configurable Threshold**: Adjust sensitivity via `XML_CONFIDENCE_THRESHOLD`
4. **Client Agnostic**: Works with any AI assistant that uses XML tools

### Configuration

Set the confidence threshold in your `.env` file:

```env
# Default: 5.0 (balanced detection)
# Higher values: Fewer false positives
# Lower values: More sensitive detection
XML_CONFIDENCE_THRESHOLD=5.0
```

### Benefits

- **No False Positives**: Won't trigger on code examples or XML discussions
- **Automatic Detection**: No manual configuration needed
- **Universal Compatibility**: Works with Roo, Cline, and any XML-based assistant
- **Performance**: Minimal overhead with pre-compiled patterns

## API Endpoints

### Available Endpoints
- `POST /v1/chat/completions` - OpenAI-compatible chat completions
- `GET /v1/models` - List available models
- `GET /v1/auth/status` - Check authentication status and configuration
- `GET /health` - Health check endpoint

## Limitations & Roadmap

### Current Limitations
- **Function calling** not supported (tools work automatically based on prompts)
- **OpenAI parameters** not yet mapped: `temperature`, `top_p`, `max_tokens`, `logit_bias`, `presence_penalty`, `frequency_penalty`
- **Multiple responses** (`n > 1`) not supported

### Planned Enhancements 
- [ ] **Multiple accounts** - Basic load balancer for distributing requests across accounts
- [ ] **Codex CLI integration** - Add support for Codex CLI models
- [ ] **Qwen CLI integration** - Add support for Qwen CLI models  
- [ ] **LLM ensemble / Council synthetic model endpoint** - Combine multiple models for enhanced responses

### Recent Improvements
- **Multimodal Images**: Full support for images in both OpenAI and file-based formats
- **SDK Integration**: Official Python SDK replaces subprocess calls
- **Real Metadata**: Accurate costs and token counts from SDK
- **Multi-auth**: Support for CLI, API key, Bedrock, and Vertex AI authentication  
- **Session IDs**: Proper session tracking and management
- **System Prompts**: Full support via SDK options
- **Session Continuity**: Conversation history across requests with session management

## Troubleshooting

1. **Claude CLI not found**:
   ```bash
   # Check Claude is in PATH
   which claude
   # Update CLAUDE_CLI_PATH in .env if needed
   ```

2. **Authentication errors**:
   ```bash
   # Test authentication with fastest model
   claude --print --model claude-3-5-haiku-20241022 "Hello"
   # If this fails, re-authenticate if needed
   ```

3. **Timeout errors**:
   - Increase `MAX_TIMEOUT` in `.env`
   - Note: Claude Code can take time for complex requests
   - SSE keepalive comments are sent every 30 seconds (configurable via `SSE_KEEPALIVE_INTERVAL`)
   - If you see connection timeouts after ~60 seconds, check your proxy/load balancer settings

## Testing

### Quick Test Suite
Test all endpoints with a simple script:
```bash
# Make sure server is running first
poetry run python test_endpoints.py
```

### Basic Test Suite
Run the comprehensive test suite:
```bash
# Make sure server is running first  
poetry run python test_basic.py

# With API key protection enabled, set TEST_API_KEY:
TEST_API_KEY=your-generated-key poetry run python test_basic.py
```

The test suite automatically detects whether API key protection is enabled and provides helpful guidance for providing the necessary authentication.

### Authentication Test
Check authentication status:
```bash
curl http://localhost:8000/v1/auth/status | python -m json.tool
```

### Development Tools
```bash
# Install development dependencies
poetry install --with dev

# Format code
poetry run black .

# Run full tests (when implemented)
poetry run pytest tests/
```

### Expected Results
All tests should show:
- **4/4 endpoint tests passing**
- **4/4 basic tests passing** 
- **Authentication method detected** (claude_cli, anthropic, bedrock, or vertex)
- **Real cost tracking** (e.g., $0.001-0.005 per test call)
- **Accurate token counts** from SDK metadata

## License

MIT License

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.
