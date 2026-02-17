import json
import logging
import logging.config
from pathlib import Path
from datetime import datetime
import random
import string
from typing import Optional


def setup_logging(config_path="config/logging_config.json"):
    """Setup logging configuration"""
    config_file = Path(config_path)
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            logging.config.dictConfig(config)
            logging.getLogger(__name__).debug("Logging configured from file")
        except Exception as e:
            print(f"Error loading logging config: {e}")
            _setup_basic_logging()
    else:
        _setup_basic_logging()


def _setup_basic_logging():
    """Setup basic logging as fallback"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    logging.getLogger(__name__).info("Using basic logging configuration")


def generate_branch_name(prefix="auto-pr", max_length=50):
    """
    Generate a unique branch name
    
    Args:
        prefix: Branch name prefix
        max_length: Maximum branch name length
    
    Returns:
        str: Unique branch name
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    branch_name = f"{prefix}-{timestamp}-{random_suffix}"
    
    # Truncate if too long
    if len(branch_name) > max_length:
        branch_name = branch_name[:max_length]
    
    return branch_name


def load_pr_template(path="templates/pr_template.md") -> str:
    """
    Load pull request template
    
    Args:
        path: Path to template file
    
    Returns:
        str: Template content or default template
    """
    template_file = Path(path)
    if template_file.exists():
        try:
            return template_file.read_text(encoding="utf-8")
        except Exception as e:
            logging.getLogger(__name__).warning(f"Error loading PR template: {e}")
    
    # Default template
    return """## 🤖 Automated Pull Request

This PR was automatically created by Auto PR Creator.

### Changes
- Automated file updates
- Co-authored commit included

### Details
- **Generated:** {timestamp}
- **Branch:** {branch}

---
*This is an automated notification*
"""


def format_timestamp(format_str="%Y-%m-%d %H:%M:%S") -> str:
    """Get formatted current timestamp"""
    return datetime.now().strftime(format_str)