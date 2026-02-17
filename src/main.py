#!/usr/bin/env python3
"""
Auto PR Creator - Enhanced version with multi-collaborator support
"""

import sys
import logging
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_manager import ConfigManager
from src.git_operations import GitOperations
from src.github_client import GitHubClient
from src.notification_manager import NotificationManager
from src.collaborator_manager import CollaboratorManager
from src import utils

logger = logging.getLogger(__name__)


class AutoPRCreator:
    """Main application class with multi-collaborator support"""

    def __init__(self, config_path="config/config.json", dry_run=False):
        utils.setup_logging()
        self.dry_run = dry_run
        self.mode = None

        if dry_run:
            logger.info("🔧 DRY RUN MODE - No changes will be made")

        try:
            self.config = ConfigManager(config_path)
            self.git = GitOperations(self.config)
            self.github = GitHubClient(self.config)
            self.notifier = NotificationManager(self.config)
            self.collaborator_manager = CollaboratorManager(self.config)

            logger.info("✅ Auto PR Creator initialized successfully")

        except Exception as e:
            logger.error(f"❌ Failed to initialize: {e}")
            raise

    def run_single_user_mode(self):
        """Original single-user mode"""
        branch = utils.generate_branch_name()
        logger.info(f"📦 Generated branch name: {branch}")

        if self.dry_run:
            logger.info(f"[DRY RUN] Would create branch: {branch}")
            logger.info("[DRY RUN] Would modify files")
            logger.info("[DRY RUN] Would commit and push changes")
            logger.info("[DRY RUN] Would create and merge PR")
            return True

        # Create branch
        self.git.create_branch(branch)

        # Modify files
        files_to_modify = self.config.get_files_to_modify()
        if not files_to_modify:
            logger.warning("No files configured to modify")
            return False

        modified_files = self.git.modify_files(files_to_modify)
        logger.info(f"📝 Modified {len(modified_files)} files")

        # Commit changes
        coauthor = self.config.get_coauthor_config()
        self.git.commit(modified_files, coauthor)

        # Push to remote
        self.git.push(branch)
        logger.info("🚀 Pushed changes to remote")

        return branch, None

    def run_collaborator_mode(self):
        """Multi-collaborator mode"""
        branch = utils.generate_branch_name(prefix="collab-pr")
        logger.info(f"🤝 Creating collaborative branch: {branch}")

        if self.dry_run:
            logger.info(f"[DRY RUN] Would create branch: {branch}")
            logger.info(f"[DRY RUN] Would create commits from {len(self.collaborator_manager.collaborators)} collaborators")
            return branch, None

        # Create branch
        self.git.create_branch(branch)

        # Create commits from multiple collaborators
        commits = self.collaborator_manager.create_multi_collaborator_commits(
            branch, 
            num_commits_per_collaborator=2
        )

        # Push all commits
        self.git.push(branch)
        logger.info(f"🚀 Pushed {len(commits)} collaborator commits to remote")

        return branch, commits

    def create_and_merge_pr(self, branch: str, commits=None):
        """Create PR and merge using squash and merge"""
        
        # Get PR configuration
        pr_config = self.config.get_pr_config()
        
        if commits:
            # Build PR body with collaborator info
            collaborators = set()
            for commit in commits:
                collaborators.add(commit['collaborator'])
            
            pr_title = f"🤝 Collaborative PR with {len(collaborators)} contributors"
            pr_body = f"""## 🤝 Multi-Collaborator Pull Request

This PR includes contributions from {len(collaborators)} team members:

### 👥 Contributors
{chr(10).join([f'- {c}' for c in collaborators])}

### 📊 Summary
- **Total commits:** {len(commits)}
- **Branch:** {branch}
- **Merge method:** Squash and merge

### ✅ Changes
Each contributor added their own files and made independent commits on the same branch.

---
*This PR demonstrates collaborative development workflow*
"""
        else:
            pr_title = pr_config.get("title", "🚀 Auto PR Update")
            pr_body = utils.load_pr_template()

        # Create PR
        pr = self.github.create_pr(branch, pr_title, pr_body)

        # Add labels
        labels = pr_config.get("labels", ["automated"])
        if commits:
            labels.append("collaborative")
        self.github.add_labels(pr["number"], labels)

        # Merge using squash and merge
        self.github.merge_pr(pr["number"], method="squash")
        logger.info(f"✅ Successfully created and squash-merged PR #{pr['number']}")

        # Send notification
        self.notifier.send_notification(pr, "merged")

        return pr

    def run(self, mode="single"):
        """
        Execute the PR creation workflow
        
        Args:
            mode: "single" or "collaborator"
        """
        try:
            self.mode = mode
            
            if mode == "collaborator":
                branch, commits = self.run_collaborator_mode()
            else:
                branch, commits = self.run_single_user_mode()

            if not self.dry_run and branch:
                pr = self.create_and_merge_pr(branch, commits)
                return True
            elif self.dry_run:
                return True
            else:
                return False

        except Exception as e:
            logger.error(f"❌ Automation failed: {e}")
            try:
                self.notifier.send_error_notification(e, {"mode": mode})
            except:
                pass
            return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Auto PR Creator - Multi-collaborator support")
    parser.add_argument("--dry-run", action="store_true", help="Simulate operations without making changes")
    parser.add_argument("--config", type=str, default="config/config.json", help="Path to configuration file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--mode", type=str, choices=["single", "collaborator"], default="single",
                       help="Run mode: single user or multi-collaborator")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    creator = AutoPRCreator(config_path=args.config, dry_run=args.dry_run)
    success = creator.run(mode=args.mode)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()