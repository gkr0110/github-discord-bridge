# GitHub-Discord Bridge

![Docker Build and Push](https://github.com/gkr0110/github-discord-bridge/actions/workflows/docker-publish.yml/badge.svg)

A lightweight, configurable bridge that forwards GitHub webhook events to Discord channels using rich embeds.

## Features

- **Pull Requests**: Detailed notifications for new PRs (title, author, branch, description).
- **Commits**: Simple alerts for pushes to the main branch.
- **Issues**: Priority alerts for issues with specific labels (e.g., `bug`, `critical`).
- **Releases**:
    - Detailed announcements for dev releases.
    - Simplified announcements for public releases.
- **Flexible Filtering**: Filter events by action, branch, labels, draft status, and more.
- **Multiple Workflows**: Route different events to different Discord channels.

## Prerequisites

- Python 3.14+ or Docker
- A GitHub Repository (to set up webhooks)
- Discord Webhook URL(s)

## Configuration

The application is configured via `config.json` and environment variables.

### Environment Variables

You must set the Discord Webhook URLs as environment variables. The variable names are defined in your `config.json`.

Example:
```bash
export DISCORD_WEBHOOK_DEV="https://discord.com/api/webhooks/..."
export DISCORD_WEBHOOK_ALERTS="https://discord.com/api/webhooks/..."
export DISCORD_WEBHOOK_ANNOUNCEMENTS="https://discord.com/api/webhooks/..."
```

### `config.json`

Define your workflows in `config.json`. Each workflow specifies:
- `name`: A descriptive name.
- `event`: The GitHub event type (e.g., `pull_request`, `push`, `issues`, `release`).
- `filters`: Conditions that must be met (e.g., `action: opened`, `branch: refs/heads/main`).
- `actions`: What to do when the event matches.
    - `webhook_env`: The environment variable containing the Discord Webhook URL.
    - `format`: The formatter to use (`pr_detailed`, `commit_simple`, `issue_priority`, `release_detailed`, `release_simple`).

## Installation & Usage

### Local Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd github-discord-bridge
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set environment variables:**
    ```bash
    export DISCORD_WEBHOOK_DEV="your_webhook_url"
    # ... set other webhooks as needed
    ```

4.  **Run the application:**
    ```bash
    python main.py
    ```
    The server will start on port 5000.

### Docker Setup

1.  **Build the image:**
    ```bash
    docker build -t github-discord-bridge .
    ```

2.  **Run the container:**
    ```bash
    docker run -d \
      -p 5000:5000 \
      -e DISCORD_WEBHOOK_DEV="your_webhook_url" \
      --name bridge \
      github-discord-bridge
    ```

## Usage as GitHub Action

You can use this bridge directly in your GitHub Actions workflows.

### Example Workflow

```yaml
name: GitHub-Discord Bridge

on:
  push:
  pull_request:
  issues:
  release:
    types: [published]

jobs:
  bridge:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Run Bridge
        uses: gkr0110/github-discord-bridge@main
        with:
          webhook_dev: ${{ secrets.DISCORD_WEBHOOK_DEV }}
          webhook_alerts: ${{ secrets.DISCORD_WEBHOOK_ALERTS }}
          webhook_announcements: ${{ secrets.DISCORD_WEBHOOK_ANNOUNCEMENTS }}
          config_file: 'config.json' # Optional, defaults to config.json
```

## GitHub Webhook Setup

1.  Go to your GitHub Repository Settings -> Webhooks.
2.  Click "Add webhook".
3.  **Payload URL**: `http://<your-server-ip>:5000/webhook`
4.  **Content type**: `application/json`
5.  **Which events would you like to trigger this webhook?**: Select "Let me select individual events" and choose the events you configured (Pull requests, Pushes, Issues, Releases).
6.  Click "Add webhook".
