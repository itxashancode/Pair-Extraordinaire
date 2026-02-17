import requests
import time
import logging
from typing import Dict, List, Optional, Any
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import sys

logger = logging.getLogger(__name__)


class GitHubClient:
    """Production-ready GitHub API client with retry logic"""

    def __init__(self, config):
        """
        Initialize GitHub client
        
        Args:
            config: ConfigManager instance
        """
        self.config = config
        self.token = config.get_github_token()

        repo = config.get_repo_config()
        self.owner = repo.get("owner")
        self.repo = repo.get("name")

        if not self.owner or not self.repo:
            raise ValueError("Repository owner and name must be configured")

        self.base_url = "https://api.github.com"
        self.api_url = f"{self.base_url}/repos/{self.owner}/{self.repo}"

        # Setup session with retry strategy
        self.session = requests.Session()
        self._setup_session()

        logger.info(f"GitHub client initialized for {self.owner}/{self.repo}")

    def _setup_session(self):
        """Setup requests session with retry strategy"""
        # Check urllib3 version for compatibility
        retry_kwargs = {
            "total": 3,
            "status_forcelist": [429, 500, 502, 503, 504],
            "backoff_factor": 1
        }
        
        # Handle different versions of urllib3
        import urllib3
        urllib3_version = tuple(map(int, urllib3.__version__.split('.')[:2]))
        
        if urllib3_version >= (2, 0):
            # Newer versions use allowed_methods
            retry_kwargs["allowed_methods"] = ["HEAD", "GET", "POST", "PUT", "DELETE"]
        else:
            # Older versions use method_whitelist
            retry_kwargs["method_whitelist"] = ["HEAD", "GET", "POST", "PUT", "DELETE"]

        retry_strategy = Retry(**retry_kwargs)

        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Headers
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
            "User-Agent": "Auto-PR-Creator/1.0"
        })

    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make HTTP request to GitHub API
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request body data
            
        Returns:
            API response as dictionary
        """
        url = f"{self.api_url}/{endpoint.lstrip('/')}"

        try:
            response = self.session.request(method, url, json=data, timeout=30)
            response.raise_for_status()
            
            # Return JSON if content exists, otherwise empty dict
            return response.json() if response.content else {}

        except requests.exceptions.RequestException as e:
            error_msg = f"GitHub API request failed: {e}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg += f" - {error_data.get('message', '')}"
                except:
                    pass
            logger.error(error_msg)
            raise

    def create_pr(self, branch: str, title: str, body: str, draft: bool = False) -> Dict[str, Any]:
        """
        Create a pull request
        
        Args:
            branch: Head branch name
            title: PR title
            body: PR body/description
            draft: Whether to create as draft PR
            
        Returns:
            Created PR data
        """
        data = {
            "title": title,
            "head": branch,
            "base": self.config.get_repo_config().get("default_branch", "main"),
            "body": body,
            "draft": draft
        }

        result = self._request("POST", "pulls", data)
        logger.info(f"Created PR #{result['number']}: {result['html_url']}")
        return result

    def add_labels(self, pr_number: int, labels: List[str]):
        """
        Add labels to PR
        
        Args:
            pr_number: PR number
            labels: List of label names
        """
        self._request("POST", f"issues/{pr_number}/labels", {"labels": labels})
        logger.debug(f"Added labels to PR #{pr_number}: {labels}")

    def merge_pr(self, pr_number: int, method: str = "merge") -> Dict[str, Any]:
        """
        Merge a pull request
        
        Args:
            pr_number: PR number
            method: Merge method (merge, squash, rebase)
            
        Returns:
            Merge result
        """
        data = {
            "merge_method": method,
            "commit_title": f"Merge PR #{pr_number} (automated)"
        }

        result = self._request("PUT", f"pulls/{pr_number}/merge", data)
        logger.info(f"Merged PR #{pr_number}")
        return result

    def get_pr(self, pr_number: int) -> Dict[str, Any]:
        """Get PR details"""
        return self._request("GET", f"pulls/{pr_number}")

    def list_prs(self, state: str = "open") -> List[Dict[str, Any]]:
        """List pull requests"""
        return self._request("GET", f"pulls?state={state}")