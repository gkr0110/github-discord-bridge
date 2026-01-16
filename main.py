import os
import json
import logging
from typing import Dict, Any, Optional, Callable
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Webhook environment variable mapping
WEBHOOK_CONFIG = {
    "dev": "DISCORD_WEBHOOK_DEV",
    "alerts": "DISCORD_WEBHOOK_ALERTS",
    "announcements": "DISCORD_WEBHOOK_ANNOUNCEMENTS"
}


def send_discord_message(webhook_url: str, embed: Optional[Dict[str, Any]] = None, content: Optional[str] = None) -> bool:
    """Send a message to Discord via webhook."""
    if not webhook_url:
        logger.error("Webhook URL is empty")
        return False
    
    payload = {}
    if embed:
        payload["embeds"] = [embed]
    if content:
        payload["content"] = content
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send Discord message: {e}")
        return False


# --- Formatters ---

def format_pull_request(data: Dict[str, Any]) -> Dict[str, Any]:
    """Format pull request events."""
    pr = data.get("pull_request", {})
    repo = data.get("repository", {})
    sender = data.get("sender", {})
    action = data.get("action", "unknown")
    
    # Skip draft PRs
    if pr.get("draft"):
        return {}
    
    # Defensive checks for required fields
    if not pr.get("title") or not repo.get("full_name"):
        logger.warning("PR event missing required fields")
        return {}
    
    action_emoji = {
        "opened": "🔄",
        "closed": "❌",
        "reopened": "↩️",
        "ready_for_review": "✅"
    }.get(action, "🔄")
    
    embed = {
        "title": f"{action_emoji} PR {action.title()}: {pr.get('title')}",
        "url": pr.get("html_url"),
        "description": pr.get("body")[:500] + "..." if pr.get("body") and len(pr.get("body")) > 500 else pr.get("body"),
        "color": 0x3498db,
        "fields": [
            {"name": "Repository", "value": repo.get("full_name"), "inline": True},
            {"name": "Branch", "value": f"`{pr.get('head', {}).get('ref')}` → `{pr.get('base', {}).get('ref')}`", "inline": True},
            {"name": "Author", "value": sender.get("login", "unknown"), "inline": True}
        ],
        "footer": {"text": f"PR #{pr.get('number')}"},
        "timestamp": pr.get("created_at")
    }
    return {"embed": embed}


def format_push(data: Dict[str, Any]) -> Dict[str, Any]:
    """Format push events."""
    commits = data.get("commits", [])
    repo = data.get("repository", {})
    sender = data.get("sender", {})
    ref = data.get("ref", "").replace("refs/heads/", "")
    
    if not commits:
        return {}
    
    # Show commit count and latest commit message
    commit_count = len(commits)
    latest = commits[0]
    message = latest.get("message", "").split("\n")[0]
    commit_url = latest.get("url", "")
    
    if commit_count == 1:
        content = f"🔨 **{sender.get('login')}** pushed to `{ref}` in `{repo.get('full_name')}`: [{message}]({commit_url})"
    else:
        content = f"🔨 **{sender.get('login')}** pushed {commit_count} commits to `{ref}` in `{repo.get('full_name')}` (latest: {message})"
    
    return {"content": content}


def format_issue(data: Dict[str, Any]) -> Dict[str, Any]:
    """Format issue events."""
    issue = data.get("issue", {})
    repo = data.get("repository", {})
    sender = data.get("sender", {})
    action = data.get("action", "unknown")
    labels = [l["name"] for l in issue.get("labels", [])]
    
    # Skip pull request issues
    if "pull_request" in issue:
        return {}
    
    # Defensive checks for required fields
    if not issue.get("title") or not repo.get("full_name"):
        logger.warning("Issue event missing required fields")
        return {}
    
    action_emoji = {
        "opened": "🚨",
        "closed": "✅",
        "reopened": "↩️",
        "labeled": "🏷️"
    }.get(action, "🚨")
    
    embed = {
        "title": f"{action_emoji} Issue {action.title()}: {issue.get('title')}",
        "url": issue.get("html_url"),
        "description": issue.get("body")[:500] + "..." if issue.get("body") and len(issue.get("body")) > 500 else issue.get("body"),
        "color": 0xe74c3c,  # Red
        "fields": [
            {"name": "Repository", "value": repo.get("full_name"), "inline": True},
            {"name": "Reporter", "value": sender.get("login", "unknown"), "inline": True}
        ],
        "footer": {"text": f"Issue #{issue.get('number')}"}
    }
    
    if labels:
        embed["fields"].append({"name": "Labels", "value": ", ".join(labels), "inline": False})
    
    return {"embed": embed}


def format_release(data: Dict[str, Any]) -> Dict[str, Any]:
    """Format release events."""
    release = data.get("release", {})
    repo = data.get("repository", {})
    
    # Skip draft releases
    if release.get("draft"):
        return {}
    
    # Defensive check for required fields
    if not release.get("tag_name") or not repo.get("full_name"):
        logger.warning("Release event missing required fields")
        return {}
    
    # For main releases, use embed; for pre-releases, use simple content
    is_prerelease = release.get("prerelease", False)
    
    if is_prerelease:
        content = f"🎉 **Pre-Release Available!** [{release.get('tag_name')}]({release.get('html_url')}) is out now!"
        return {"content": content}
    
    embed = {
        "title": f"🚀 New Release: {release.get('name') or release.get('tag_name')}",
        "url": release.get("html_url"),
        "description": release.get("body")[:1000] + "..." if release.get("body") and len(release.get("body")) > 1000 else release.get("body"),
        "color": 0xf1c40f,  # Yellow
        "fields": [
            {"name": "Tag", "value": release.get("tag_name"), "inline": True},
            {"name": "Repository", "value": repo.get("full_name"), "inline": True}
        ],
        "footer": {"text": "Release Notes"}
    }
    return {"embed": embed}


def get_webhook_for_event(event_type: str, data: Dict[str, Any]) -> Optional[str]:
    """Determine which webhook to use based on event type and context."""
    # Pull requests and issues → dev channel
    if event_type in ("pull_request", "issues"):
        return os.environ.get(WEBHOOK_CONFIG["dev"])
    
    # Push to main → alerts channel
    if event_type == "push":
        ref = data.get("ref", "").replace("refs/heads/", "")
        if ref == "main":
            return os.environ.get(WEBHOOK_CONFIG["alerts"])
        return os.environ.get(WEBHOOK_CONFIG["dev"])
    
    # Releases
    if event_type == "release":
        is_prerelease = data.get("release", {}).get("prerelease", False)
        # Pre-releases and dev announcements → dev
        if is_prerelease:
            return os.environ.get(WEBHOOK_CONFIG["dev"])
        # Main releases → announcements
        return os.environ.get(WEBHOOK_CONFIG["announcements"])
    
    return None


def get_formatter_for_event(event_type: str) -> Optional[Callable]:
    """Get the appropriate formatter for the event type."""
    formatters = {
        "pull_request": format_pull_request,
        "push": format_push,
        "issues": format_issue,
        "release": format_release
    }
    return formatters.get(event_type)



def process_event(event_type: str, data: Dict[str, Any]) -> int:
    """Process a GitHub webhook event and send to Discord if applicable."""
    # Ignore ping events
    if event_type == "ping":
        logger.info("Received ping event")
        return 0
    
    # Get appropriate formatter
    formatter = get_formatter_for_event(event_type)
    if not formatter:
        logger.info(f"No handler for event type: {event_type}")
        return 0
    
    # Get message data
    message_data = formatter(data)
    if not message_data:
        logger.info(f"No message generated for event: {event_type}")
        return 0
    
    # Get webhook URL
    webhook_url = get_webhook_for_event(event_type, data)
    if not webhook_url:
        logger.warning(f"No webhook configured for event type: {event_type}")
        return 0
    
    # Send message
    action = data.get("action", "")
    logger.info(f"Processing {event_type} event (action: {action})")
    success = send_discord_message(webhook_url, embed=message_data.get("embed"), content=message_data.get("content"))
    
    return 1 if success else 0


@app.route("/webhook", methods=["POST"])
def webhook():
    """Handle GitHub webhook POST requests."""
    event_type = request.headers.get("X-GitHub-Event")
    
    if not event_type:
        logger.warning("Webhook received without X-GitHub-Event header")
        return jsonify({"error": "Missing X-GitHub-Event header"}), 400
    
    data = request.json
    if not data:
        logger.warning(f"Webhook received for {event_type} with no data")
        return jsonify({"error": "No data received"}), 400
    
    if event_type == "ping":
        return jsonify({"message": "Pong!"}), 200

    triggered_actions = process_event(event_type, data)
    return jsonify({"message": f"Processed event. Triggered {triggered_actions} actions."}), 200


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy"}), 200


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({"error": "Not found. Use POST /webhook for GitHub events or GET /health for health check."}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    if os.environ.get("GITHUB_ACTIONS") == "true":
        # Run in "one-shot" mode for GitHub Actions
        logger.info("Running in GitHub Action mode")
        
        event_path = os.environ.get("GITHUB_EVENT_PATH")
        event_name = os.environ.get("GITHUB_EVENT_NAME")
        
        if not event_path or not event_name:
            logger.error("Missing GITHUB_EVENT_PATH or GITHUB_EVENT_NAME")
            exit(1)
        
        try:
            with open(event_path, "r") as f:
                event_data = json.load(f)
        except FileNotFoundError:
            logger.error(f"Event file not found: {event_path}")
            exit(1)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse event JSON: {e}")
            exit(1)
        except Exception as e:
            logger.error(f"Failed to load event data: {e}")
            exit(1)
        
        count = process_event(event_name, event_data)
        logger.info(f"Processed event '{event_name}'. Triggered {count} actions.")
    else:
        # Run in server mode
        logger.info("Starting GitHub-Discord Bridge server on http://0.0.0.0:5000")
        logger.info("Endpoints:")
        logger.info("  POST /webhook - GitHub webhook handler")
        logger.info("  GET  /health  - Health check")
        app.run(host="0.0.0.0", port=5000)

