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

- A GitHub Repository.
- A Discord Server with permissions to manage webhooks.

### Getting a Discord Webhook URL
1. Open Discord and go to the channel where you want notifications.
2. Click the **Edit Channel** (gear icon) next to the channel name.
3. Go to **Integrations** -> **Webhooks**.
4. Click **New Webhook**.
5. Copy the **Webhook URL**. You will need this later.

## Configuration

The application is configured via `config.json` and environment variables.

### 1. Environment Variables
You must set the Discord Webhook URLs as environment variables. The variable names are defined in your `config.json`.

```bash
export DISCORD_WEBHOOK_DEV="https://discord.com/api/webhooks/..."
export DISCORD_WEBHOOK_ALERTS="https://discord.com/api/webhooks/..."
export DISCORD_WEBHOOK_ANNOUNCEMENTS="https://discord.com/api/webhooks/..."
```

### 2. `config.json`
The `config.json` file controls which GitHub events are sent to Discord.

**Structure:**
- `workflows`: A list of workflow definitions.
  - `name`: Name of the workflow (for logging).
  - `event`: The GitHub event to listen for (e.g., `pull_request`, `push`, `issues`, `release`).
  - `filters`: Rules to match specific events.
    - `action`: (Optional) Match specific action (e.g., `opened`, `closed`, `published`).
    - `branch`: (Optional) Match specific branch (e.g., `refs/heads/main`).
    - `labels_include`: (Optional) List of labels to match (for issues).
  - `actions`: List of actions to take.
    - `webhook_env`: The environment variable name that holds the Discord Webhook URL.
    - `format`: The message format (`pr_detailed`, `commit_simple`, `issue_priority`, `release_detailed`, `release_simple`).

**Example:**
```json
{
  "workflows": [
    {
      "name": "New PRs",
      "event": "pull_request",
      "filters": { "action": "opened" },
      "actions": [{ "webhook_env": "DISCORD_WEBHOOK_DEV", "format": "pr_detailed" }]
    }
  ]
}
```

## Deployment Options

You can run this bridge in two ways:
1.  **GitHub Action**: Runs ephemerally within your GitHub Actions pipeline. Easiest setup for single repositories.
2.  **Standalone Server**: Runs as a long-running web server (using Docker or Python). Suitable if you want to receive webhooks from multiple repos or don't want to use GitHub Actions.

---

### Option 1: GitHub Action

You can use this bridge directly in your GitHub Actions workflows.

#### Example Workflow

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

---

### Option 2: Standalone Server

#### Local Setup

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

#### Docker Setup

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

#### GitHub Webhook Setup (For Standalone Mode)

1.  Go to your GitHub Repository Settings -> Webhooks.
2.  Click "Add webhook".
3.  **Payload URL**: `http://<your-server-ip>:5000/webhook`
4.  **Content type**: `application/json`
5.  **Which events would you like to trigger this webhook?**: Select "Let me select individual events" and choose the events you configured (Pull requests, Pushes, Issues, Releases).
6.  Click "Add webhook".
