import json
import os
from pathlib import Path
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """Production-ready configuration manager with validation"""

    def __init__(self, config_path="config/config.json"):
        self.config_path = Path(config_path).resolve()
        self.config = {}
        self._load_config()
        self._load_env()
        self._validate_config()

    def _load_config(self):
        """Load JSON configuration file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
            logger.info(f"Configuration loaded from {self.config_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}")

    def _load_env(self):
        """Load environment variables from .env file"""
        env_path = Path(".env")
        if env_path.exists():
            load_dotenv(env_path)
            logger.debug("Environment variables loaded from .env")
        else:
            logger.warning(".env file not found, using system environment variables")

    def _validate_config(self):
        """Validate required configuration sections"""
        required_sections = ["github", "files"]
        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"Missing required config section: {section}")

        # Validate GitHub repository config
        repo_config = self.get_repo_config()
        if not repo_config.get("owner") or not repo_config.get("name"):
            raise ValueError("GitHub repository owner and name must be configured")

    def get_github_token(self):
        """Get GitHub token from environment variables"""
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError(
                "GITHUB_TOKEN not found in environment variables. "
                "Please set it in .env file or system environment."
            )
        return token

    def get_discord_webhook(self):
        """Get Discord webhook URL from environment variables"""
        webhook = os.getenv("DISCORD_WEBHOOK")
        return webhook  # Optional, can be None

    def get_slack_webhook(self):
        """Get Slack webhook URL from environment variables"""
        webhook = os.getenv("SLACK_WEBHOOK")
        return webhook  # Optional, can be None

    def get_repo_config(self):
        """Get repository configuration"""
        return self.config.get("github", {}).get("repository", {})

    def get_merge_config(self):
        """Get merge configuration"""
        return self.config.get("github", {}).get("merge", {})

    def get_coauthor_config(self):
        """Get co-author configuration"""
        return self.config.get("coauthor", {})

    def get_notification_config(self):
        """Get notification configuration"""
        return self.config.get("notifications", {})

    def get_files_to_modify(self):
        """Get list of files to modify"""
        return self.config.get("files", {}).get("to_modify", [])

    def get_pr_config(self):
        """Get pull request configuration"""
        return self.config.get("pull_request", {})