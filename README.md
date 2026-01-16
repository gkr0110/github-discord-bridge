# GitHub-Discord Bridge

![Docker Build and Push](https://github.com/gkr0110/github-discord-bridge/actions/workflows/docker-publish.yml/badge.svg)

A lightweight, zero-config bridge that forwards GitHub webhook events to Discord channels with automatic formatting based on event type.

## Features

- **Zero Configuration**: No config file needed! Formatting is automatically detected based on the event type.
- **Pull Requests**: Rich notifications for opened/closed/reopened PRs with details, author, and branch info.
- **Commits**: Smart push notifications to alerts channel for main branch, dev channel for others.
- **Issues**: Detailed issue notifications with labels and reporter info.
- **Releases**: 
  - Rich embeds for main releases (to announcements channel).
  - Simple messages for pre-releases (to dev channel).
- **Automatic Routing**: Events are routed to the appropriate Discord channel based on context.
- **Draft Filtering**: Automatically ignores draft PRs and releases.

## How It Works

The bridge automatically determines which Discord webhook to use based on the event type and context:

| Event | Condition | Webhook |
|-------|-----------|---------|
| Pull Request | Any action (except draft) | `DISCORD_WEBHOOK_DEV` |
| Push | To main branch | `DISCORD_WEBHOOK_ALERTS` |
| Push | To other branches | `DISCORD_WEBHOOK_DEV` |
| Issue | Any action (except PRs) | `DISCORD_WEBHOOK_DEV` |
| Release | Pre-release | `DISCORD_WEBHOOK_DEV` |
| Release | Main release | `DISCORD_WEBHOOK_ANNOUNCEMENTS` |

## Prerequisites

- A GitHub Repository.
- A Discord Server with permissions to manage webhooks.

### Getting Discord Webhook URLs

For each Discord channel where you want notifications:

1. Open Discord and go to the channel.
2. Click the **Settings** icon (gear) next to the channel name.
3. Go to **Integrations** → **Webhooks**.
4. Click **New Webhook**, then **Copy Webhook URL**.
5. Save these URLs as repository secrets (see deployment instructions).

## Configuration

The bridge requires only **environment variables** pointing to Discord webhook URLs. No config file needed!

### Environment Variables

Set these as repository secrets or environment variables:

```bash
DISCORD_WEBHOOK_DEV          # For PRs, issues, pre-releases, dev branch pushes
DISCORD_WEBHOOK_ALERTS       # For main branch pushes
DISCORD_WEBHOOK_ANNOUNCEMENTS # For main releases
```

All are optional - just set the ones you need. If a webhook isn't configured for an event type, that event is skipped.

## Deployment Options

### Option 1: GitHub Action (Recommended for Single Repo)

The easiest setup - runs within your GitHub Actions pipeline.

#### Example Workflow

```yaml
name: Notify Discord

on:
  push:
  pull_request:
  issues:
  release:
    types: [published, created]

jobs:
  discord-bridge:
    runs-on: ubuntu-latest
    steps:
      - name: GitHub-Discord Bridge
        uses: gkr0110/github-discord-bridge@main
        with:
          webhook_dev: ${{ secrets.DISCORD_WEBHOOK_DEV }}
          webhook_alerts: ${{ secrets.DISCORD_WEBHOOK_ALERTS }}
          webhook_announcements: ${{ secrets.DISCORD_WEBHOOK_ANNOUNCEMENTS }}
```

#### Setup Instructions

1. Add the workflow file above to `.github/workflows/discord-notify.yml` in your repository.
2. Go to **Settings** → **Secrets and variables** → **Actions**.
3. Add the three secrets: `DISCORD_WEBHOOK_DEV`, `DISCORD_WEBHOOK_ALERTS`, `DISCORD_WEBHOOK_ANNOUNCEMENTS`.
4. Commit and push - notifications will start immediately!

---

### Option 2: Standalone Server (For Multiple Repos or Webhooks)

Run the bridge as a persistent web server.

#### Local Development

1. **Clone and setup:**
   ```bash
   git clone <repository-url>
   cd github-discord-bridge
   pip install -r requirements.txt
   ```

2. **Set environment variables:**
   ```bash
   export DISCORD_WEBHOOK_DEV="https://discord.com/api/webhooks/..."
   export DISCORD_WEBHOOK_ALERTS="https://discord.com/api/webhooks/..."
   export DISCORD_WEBHOOK_ANNOUNCEMENTS="https://discord.com/api/webhooks/..."
   ```

3. **Run:**
   ```bash
   python main.py
   ```
   Server runs on `http://localhost:5000/webhook`

#### Docker Deployment

1. **Build:**
   ```bash
   docker build -t github-discord-bridge .
   ```

2. **Run:**
   ```bash
   docker run -d \
     -p 5000:5000 \
     -e DISCORD_WEBHOOK_DEV="your_webhook_url" \
     -e DISCORD_WEBHOOK_ALERTS="your_webhook_url" \
     -e DISCORD_WEBHOOK_ANNOUNCEMENTS="your_webhook_url" \
     --name bridge \
     github-discord-bridge
   ```

#### Configure GitHub Webhooks

For each repository:

1. Go to **Settings** → **Webhooks** → **Add webhook**.
2. **Payload URL**: `https://your-server.com:5000/webhook`
3. **Content type**: `application/json`
4. **Events**: Select the events you want to monitor (Pushes, Pull requests, Issues, Releases).
5. **Active**: Check the box.
6. Click **Add webhook**.

Test the webhook from GitHub's webhook settings page.

---

## Message Formatting

The bridge automatically formats messages based on event type. Here are examples:

### Pull Request
```
🔄 PR Opened: Fix authentication bug
Repository: myorg/myrepo
Branch: `feature/auth` → `main`
Author: johndoe
```

### Main Branch Push
```
🔨 johndoe pushed 3 commits to `main` in `myorg/myrepo` (latest: Merge pull request #42)
```

### Issue
```
🚨 Issue Opened: Memory leak in cache system
Repository: myorg/myrepo
Reporter: janedoe
Labels: bug, critical
```

### Release
```
🚀 New Release: v1.2.0
Tag: v1.2.0
Repository: myorg/myrepo
```

## Health Check

Both GitHub Action and server modes support a health check endpoint:

```bash
curl http://localhost:5000/health
# Returns: {"status": "healthy"}
```

## Troubleshooting

**Events not showing up in Discord?**
- Check that webhook URLs are set correctly (they should start with `https://discord.com/api/webhooks/`).
- Verify the webhook channel still exists and is accessible.
- Check logs for any error messages.

**Wrong channel receiving events?**
- Review the routing table above to ensure your webhooks are assigned to the expected channels.

**Draft PRs/Releases appearing?**
- Draft content is automatically filtered out - this is by design.

## License

MIT