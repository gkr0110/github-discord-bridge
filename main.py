import os
import json
import logging
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration
try:
    with open("config.json", "r") as f:
        CONFIG = json.load(f)
except FileNotFoundError:
    logger.error("config.json not found!")
    CONFIG = {"workflows": []}

def send_discord_message(webhook_url, embed=None, content=None):
    if not webhook_url:
        logger.error("Webhook URL is empty")
        return False
    
    payload = {}
    if embed:
        payload["embeds"] = [embed]
    if content:
        payload["content"] = content
    
    try:
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send Discord message: {e}")
        return False

# --- Formatters ---

def format_pr_detailed(data):
    pr = data.get("pull_request", {})
    repo = data.get("repository", {})
    sender = data.get("sender", {})
    
    embed = {
        "title": f"🔄 New Pull Request: {pr.get('title')}",
        "url": pr.get("html_url"),
        "description": pr.get("body")[:500] + "..." if pr.get("body") and len(pr.get("body")) > 500 else pr.get("body"),
        "color": 0x3498db,
        "fields": [
            {"name": "Repository", "value": repo.get("full_name"), "inline": True},
            {"name": "Branch", "value": f"`{pr.get('head', {}).get('ref')}` → `{pr.get('base', {}).get('ref')}`", "inline": True},
            {"name": "Author", "value": sender.get("login"), "inline": True}
        ],
        "footer": {"text": f"PR #{pr.get('number')}"},
        "timestamp": pr.get("created_at")
    }
    return {"embed": embed}

def format_commit_simple(data):
    commits = data.get("commits", [])
    if not commits:
        return None
    
    repo = data.get("repository", {})
    sender = data.get("sender", {})
    ref = data.get("ref", "").replace("refs/heads/", "")
    
    # Just show the latest commit or a summary
    latest = commits[0]
    message = latest.get("message", "").split("\n")[0]
    
    content = f"🔨 **{sender.get('login')}** pushed to `{ref}` in `{repo.get('full_name')}`: {message}"
    return {"content": content}

def format_issue_priority(data):
    issue = data.get("issue", {})
    repo = data.get("repository", {})
    sender = data.get("sender", {})
    labels = [l["name"] for l in issue.get("labels", [])]
    
    embed = {
        "title": f"🚨 New Priority Issue: {issue.get('title')}",
        "url": issue.get("html_url"),
        "description": issue.get("body")[:500] + "..." if issue.get("body") and len(issue.get("body")) > 500 else issue.get("body"),
        "color": 0xe74c3c, # Red
        "fields": [
            {"name": "Repository", "value": repo.get("full_name"), "inline": True},
            {"name": "Reporter", "value": sender.get("login"), "inline": True},
            {"name": "Labels", "value": ", ".join(labels), "inline": False}
        ],
        "footer": {"text": f"Issue #{issue.get('number')}"}
    }
    return {"embed": embed}

def format_release_detailed(data):
    release = data.get("release", {})
    repo = data.get("repository", {})
    
    embed = {
        "title": f"🚀 New Release: {release.get('name') or release.get('tag_name')}",
        "url": release.get("html_url"),
        "description": release.get("body")[:1000] + "..." if release.get("body") and len(release.get("body")) > 1000 else release.get("body"),
        "color": 0xf1c40f, # Yellow
        "fields": [
            {"name": "Tag", "value": release.get("tag_name"), "inline": True},
            {"name": "Repository", "value": repo.get("full_name"), "inline": True}
        ],
        "footer": {"text": "Release Notes"}
    }
    return {"embed": embed}

def format_release_simple(data):
    release = data.get("release", {})
    content = f"🎉 **New Release Available!** [{release.get('tag_name')}]({release.get('html_url')}) is out now!"
    return {"content": content}

FORMATTERS = {
    "pr_detailed": format_pr_detailed,
    "commit_simple": format_commit_simple,
    "issue_priority": format_issue_priority,
    "release_detailed": format_release_detailed,
    "release_simple": format_release_simple
}

# --- Logic ---

def check_filters(filters, data, event_type):
    if not filters:
        return True
        
    # Check action
    if "action" in filters:
        if data.get("action") != filters["action"]:
            return False
            
    # Check draft status (PRs and Releases)
    if "is_draft" in filters:
        is_draft = False
        if event_type == "pull_request":
            is_draft = data.get("pull_request", {}).get("draft", False)
        elif event_type == "release":
            is_draft = data.get("release", {}).get("draft", False)
        
        if is_draft != filters["is_draft"]:
            return False

    # Check prerelease (Releases)
    if "is_prerelease" in filters and event_type == "release":
        is_prerelease = data.get("release", {}).get("prerelease", False)
        if is_prerelease != filters["is_prerelease"]:
            return False
            
    # Check branch (Push)
    if "branch" in filters and event_type == "push":
        if data.get("ref") != filters["branch"]:
            return False
            
    # Check labels (Issues)
    if "labels_include" in filters and event_type == "issues":
        issue_labels = [l["name"].lower() for l in data.get("issue", {}).get("labels", [])]
        required_labels = [l.lower() for l in filters["labels_include"]]
        # Check if ANY of the required labels are present
        if not any(label in issue_labels for label in required_labels):
            return False
            
    return True

@app.route("/webhook", methods=["POST"])
def webhook():
    event_type = request.headers.get("X-GitHub-Event")
    data = request.json
    
    if not data:
        return jsonify({"error": "No data received"}), 400
        
    if event_type == "ping":
        return jsonify({"message": "Pong!"}), 200

    triggered_actions = 0
    
    for workflow in CONFIG.get("workflows", []):
        if workflow.get("event") != event_type:
            continue
            
        if not check_filters(workflow.get("filters"), data, event_type):
            continue
            
        logger.info(f"Triggering workflow: {workflow.get('name')}")
        
        for action in workflow.get("actions", []):
            webhook_env = action.get("webhook_env")
            webhook_url = os.environ.get(webhook_env)
            
            if not webhook_url:
                logger.warning(f"Webhook URL env var {webhook_env} not set for workflow {workflow.get('name')}")
                continue
                
            formatter_name = action.get("format")
            formatter = FORMATTERS.get(formatter_name)
            
            if formatter:
                message_data = formatter(data)
                if message_data:
                    send_discord_message(webhook_url, embed=message_data.get("embed"), content=message_data.get("content"))
                    triggered_actions += 1
            else:
                logger.error(f"Unknown formatter: {formatter_name}")

    return jsonify({"message": f"Processed event. Triggered {triggered_actions} actions."}), 200

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
