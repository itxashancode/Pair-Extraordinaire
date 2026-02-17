import requests
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class NotificationManager:
    """Enhanced notification manager with Discord and Slack support"""

    def __init__(self, config):
        """
        Initialize notification manager
        
        Args:
            config: ConfigManager instance
        """
        self.config = config
        self.notification_config = config.get_notification_config()

        # Get webhooks from environment
        self.discord_webhook = config.get_discord_webhook()
        self.slack_webhook = config.get_slack_webhook()

        # Log which notifications are enabled
        enabled = []
        if self.discord_webhook:
            enabled.append("Discord")
        if self.slack_webhook:
            enabled.append("Slack")

        if enabled:
            logger.info(f"Notifications enabled for: {', '.join(enabled)}")
        else:
            logger.info("No notifications configured")

    def send_notification(self, pr: Dict, status: str = "success"):
        """
        Send notification about PR status
        
        Args:
            pr: Pull request data from GitHub API
            status: Status of the operation (success, failed, merged)
        """
        if not self.discord_webhook and not self.slack_webhook:
            logger.debug("No notification channels configured, skipping")
            return

        # Create message
        message = self._format_message(pr, status)

        # Send to Discord if configured
        if self.discord_webhook:
            self._send_discord(message, pr)

        # Send to Slack if configured
        if self.slack_webhook:
            self._send_slack(message, pr)

    def _format_message(self, pr: Dict, status: str) -> str:
        """
        Format notification message
        
        Args:
            pr: Pull request data
            status: Status string
            
        Returns:
            Formatted message
        """
        repo = self.config.get_repo_config()
        repo_name = f"{repo.get('owner')}/{repo.get('name')}"

        # Status emoji
        emoji = {
            "success": "✅",
            "merged": "🚀",
            "failed": "❌",
            "created": "🆕"
        }.get(status, "📋")

        # Format message
        message = (
            f"{emoji} **Auto PR Creator - {status.upper()}**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**Repository:** `{repo_name}`\n"
            f"**PR #{pr.get('number')}:** {pr.get('title', 'Untitled')}\n"
            f"**Status:** {status}\n"
            f"**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔗 {pr.get('html_url', 'No URL')}"
        )

        return message

    def _send_discord(self, message: str, pr: Dict):
        """
        Send notification to Discord webhook
        
        Args:
            message: Formatted message
            pr: Pull request data
        """
        if not self.discord_webhook:
            return

        try:
            # Discord webhook payload
            payload = {
                "content": message,
                "username": "Auto PR Creator",
                "avatar_url": "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png",
                "embeds": [{
                    "title": pr.get('title', 'Pull Request'),
                    "url": pr.get('html_url', ''),
                    "color": 0x2ecc71 if pr.get('merged') else 0x3498db,
                    "fields": [
                        {
                            "name": "Branch",
                            "value": f"`{pr.get('head', {}).get('ref', 'unknown')}` → `{pr.get('base', {}).get('ref', 'main')}`",
                            "inline": True
                        },
                        {
                            "name": "Created by",
                            "value": pr.get('user', {}).get('login', 'auto'),
                            "inline": True
                        }
                    ],
                    "timestamp": datetime.now().isoformat()
                }]
            }

            response = requests.post(self.discord_webhook, json=payload, timeout=10)
            response.raise_for_status()
            logger.debug(f"Discord notification sent for PR #{pr.get('number')}")

        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")

    def _send_slack(self, message: str, pr: Dict):
        """
        Send notification to Slack webhook
        
        Args:
            message: Formatted message
            pr: Pull request data
        """
        if not self.slack_webhook:
            return

        try:
            # Slack webhook payload
            payload = {
                "text": message,
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": message
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"<{pr.get('html_url', '#')}|View Pull Request>"
                            }
                        ]
                    }
                ]
            }

            response = requests.post(self.slack_webhook, json=payload, timeout=10)
            response.raise_for_status()
            logger.debug(f"Slack notification sent for PR #{pr.get('number')}")

        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")

    def send_error_notification(self, error: Exception, context: Dict = None):
        """
        Send error notification
        
        Args:
            error: Exception that occurred
            context: Additional context information
        """
        if not self.discord_webhook and not self.slack_webhook:
            return

        error_message = (
            f"❌ **Auto PR Creator - ERROR**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**Error:** `{str(error)}`\n"
            f"**Type:** `{type(error).__name__}`\n"
            f"**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )

        if context:
            error_message += f"**Context:** `{context}`\n"

        error_message += "━━━━━━━━━━━━━━━━━━━━━━"

        # Send to Discord
        if self.discord_webhook:
            try:
                payload = {"content": error_message}
                requests.post(self.discord_webhook, json=payload, timeout=10)
            except Exception as e:
                logger.error(f"Failed to send error to Discord: {e}")

        # Send to Slack
        if self.slack_webhook:
            try:
                payload = {"text": error_message}
                requests.post(self.slack_webhook, json=payload, timeout=10)
            except Exception as e:
                logger.error(f"Failed to send error to Slack: {e}")