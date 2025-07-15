"""
Git utilities for change detection and repository operations.

This module provides Git integration for detecting changes, getting file versions,
and analyzing repository history for semantic diff detection.
"""

import logging
import subprocess
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class GitError(Exception):
    """Git operation error."""

    pass


class GitOperations:
    """Git operations for change detection and file retrieval."""

    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = repo_path or Path.cwd()
        self._validate_git_repo()

    def _validate_git_repo(self) -> None:
        """Validate that the directory is a Git repository."""
        git_dir = self.repo_path / ".git"
        if not git_dir.exists():
            # Check if we're in a subdirectory of a git repo
            current = self.repo_path
            while current != current.parent:
                if (current / ".git").exists():
                    self.repo_path = current
                    return
                current = current.parent

            raise GitError(f"Not a git repository: {self.repo_path}")

        logger.debug(f"Git repository found at: {self.repo_path}")

    def _run_git_command(
        self, args: list[str], check_output: bool = True, cwd: Optional[Path] = None
    ) -> subprocess.CompletedProcess:
        """
        Run a git command and return the result.

        Args:
            args: Git command arguments.
            check_output: Whether to capture output.
            cwd: Working directory for the command.

        Returns:
            CompletedProcess result.

        Raises:
            GitError: If the git command fails.
        """
        cmd = ["git"] + args
        work_dir = cwd or self.repo_path

        try:
            result = subprocess.run(
                cmd, cwd=work_dir, capture_output=check_output, text=True, check=False
            )

            if result.returncode != 0:
                error_msg = f"Git command failed: {' '.join(cmd)}\n"
                if result.stderr:
                    error_msg += f"Error: {result.stderr}"
                raise GitError(error_msg)

            return result
        except FileNotFoundError:
            raise GitError("Git is not installed or not in PATH")
        except Exception as e:
            raise GitError(f"Git command error: {e}")

    def get_changed_files(
        self,
        base_commit: str = "HEAD~1",
        target_commit: str = "HEAD",
        include_untracked: bool = False,
    ) -> list[str]:
        """
        Get list of changed files between commits.

        Args:
            base_commit: Base commit for comparison.
            target_commit: Target commit for comparison.
            include_untracked: Whether to include untracked files.

        Returns:
            List of changed file paths.
        """
        try:
            # Get modified/added/deleted files
            result = self._run_git_command(
                ["diff", "--name-only", f"{base_commit}...{target_commit}"]
            )

            changed_files = (
                result.stdout.strip().split("\n") if result.stdout.strip() else []
            )

            # Add untracked files if requested
            if include_untracked:
                untracked_result = self._run_git_command(
                    ["ls-files", "--others", "--exclude-standard"]
                )
                untracked_files = (
                    untracked_result.stdout.strip().split("\n")
                    if untracked_result.stdout.strip()
                    else []
                )
                changed_files.extend(untracked_files)

            # Filter out empty strings and convert to absolute paths
            filtered_files = []
            for file_path in changed_files:
                if file_path:
                    abs_path = self.repo_path / file_path
                    if (
                        abs_path.exists() or not include_untracked
                    ):  # Include deleted files from diff
                        filtered_files.append(file_path)

            logger.debug(f"Found {len(filtered_files)} changed files")
            return filtered_files

        except GitError:
            raise
        except Exception as e:
            raise GitError(f"Failed to get changed files: {e}")

    def get_file_at_commit(self, file_path: str, commit: str) -> Optional[str]:
        """
        Get file content at a specific commit.

        Args:
            file_path: Path to the file relative to repo root.
            commit: Commit hash or reference.

        Returns:
            File content as string, or None if file doesn't exist at commit.
        """
        try:
            result = self._run_git_command(["show", f"{commit}:{file_path}"])
            return result.stdout
        except GitError as e:
            if "does not exist" in str(e) or "Path does not exist" in str(e):
                logger.debug(f"File {file_path} does not exist at commit {commit}")
                return None
            raise

    def get_current_file_content(self, file_path: str) -> Optional[str]:
        """
        Get current file content from working directory.

        Args:
            file_path: Path to the file relative to repo root.

        Returns:
            File content as string, or None if file doesn't exist.
        """
        try:
            full_path = self.repo_path / file_path
            if not full_path.exists():
                return None

            with open(full_path, encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(full_path, encoding="latin-1") as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"Failed to read file {file_path}: {e}")
                return None
        except Exception as e:
            logger.warning(f"Failed to read file {file_path}: {e}")
            return None

    def get_file_status(self, file_path: str) -> str:
        """
        Get the status of a file (modified, added, deleted, etc.).

        Args:
            file_path: Path to the file relative to repo root.

        Returns:
            Status string (M, A, D, etc.).
        """
        try:
            result = self._run_git_command(["status", "--porcelain", file_path])

            if result.stdout.strip():
                return result.stdout.strip()[:2]  # First two characters indicate status
            return ""
        except GitError:
            return ""

    def get_commit_info(self, commit: str = "HEAD") -> dict[str, str]:
        """
        Get information about a commit.

        Args:
            commit: Commit hash or reference.

        Returns:
            Dictionary with commit information.
        """
        try:
            # Get commit details
            result = self._run_git_command(
                ["show", "--format=%H|%an|%ae|%ad|%s", "--no-patch", commit]
            )

            parts = result.stdout.strip().split("|")
            if len(parts) >= 5:
                return {
                    "hash": parts[0],
                    "author_name": parts[1],
                    "author_email": parts[2],
                    "date": parts[3],
                    "message": "|".join(parts[4:]),  # In case message contains |
                }

            return {"error": "Unable to parse commit info"}
        except GitError as e:
            return {"error": str(e)}

    def get_branch_name(self) -> str:
        """
        Get current branch name.

        Returns:
            Current branch name.
        """
        try:
            result = self._run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
            return result.stdout.strip()
        except GitError:
            return "unknown"

    def get_remote_branches(self) -> list[str]:
        """
        Get list of remote branches.

        Returns:
            List of remote branch names.
        """
        try:
            result = self._run_git_command(["branch", "-r"])

            branches = []
            for line in result.stdout.strip().split("\n"):
                branch = line.strip()
                if branch and not branch.startswith("origin/HEAD"):
                    branches.append(branch)

            return branches
        except GitError:
            return []

    def get_file_history(
        self, file_path: str, max_commits: int = 10
    ) -> list[dict[str, Any]]:
        """
        Get commit history for a specific file.

        Args:
            file_path: Path to the file relative to repo root.
            max_commits: Maximum number of commits to retrieve.

        Returns:
            List of commit information dictionaries.
        """
        try:
            result = self._run_git_command(
                ["log", "--format=%H|%an|%ad|%s", f"-{max_commits}", "--", file_path]
            )

            history = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split("|")
                    if len(parts) >= 4:
                        history.append(
                            {
                                "hash": parts[0],
                                "author": parts[1],
                                "date": parts[2],
                                "message": "|".join(parts[3:]),
                            }
                        )

            return history
        except GitError:
            return []

    def compare_files_between_commits(
        self, file_path: str, commit1: str, commit2: str
    ) -> dict[str, Any]:
        """
        Compare a file between two commits.

        Args:
            file_path: Path to the file relative to repo root.
            commit1: First commit for comparison.
            commit2: Second commit for comparison.

        Returns:
            Dictionary with comparison results.
        """
        try:
            # Get diff statistics
            diff_result = self._run_git_command(
                ["diff", "--numstat", f"{commit1}..{commit2}", "--", file_path]
            )

            comparison = {
                "file_path": file_path,
                "commit1": commit1,
                "commit2": commit2,
                "additions": 0,
                "deletions": 0,
                "changes": 0,
            }

            if diff_result.stdout.strip():
                parts = diff_result.stdout.strip().split("\t")
                if len(parts) >= 2:
                    try:
                        comparison["additions"] = (
                            int(parts[0]) if parts[0] != "-" else 0
                        )
                        comparison["deletions"] = (
                            int(parts[1]) if parts[1] != "-" else 0
                        )
                        comparison["changes"] = (
                            comparison["additions"] + comparison["deletions"]
                        )
                    except ValueError:
                        pass

            return comparison
        except GitError as e:
            return {"error": str(e)}

    def is_file_tracked(self, file_path: str) -> bool:
        """
        Check if a file is tracked by Git.

        Args:
            file_path: Path to the file relative to repo root.

        Returns:
            True if file is tracked, False otherwise.
        """
        try:
            self._run_git_command(["ls-files", "--error-unmatch", file_path])
            return True
        except GitError:
            return False

    def get_repo_info(self) -> dict[str, Any]:
        """
        Get general repository information.

        Returns:
            Dictionary with repository information.
        """
        try:
            # Get remote URL
            try:
                remote_result = self._run_git_command(["remote", "get-url", "origin"])
                remote_url = remote_result.stdout.strip()
            except GitError:
                remote_url = "unknown"

            # Get total commit count
            try:
                count_result = self._run_git_command(["rev-list", "--count", "HEAD"])
                commit_count = int(count_result.stdout.strip())
            except (GitError, ValueError):
                commit_count = 0

            return {
                "path": str(self.repo_path),
                "branch": self.get_branch_name(),
                "remote_url": remote_url,
                "commit_count": commit_count,
                "last_commit": self.get_commit_info("HEAD"),
            }
        except Exception as e:
            return {"error": str(e)}


def is_git_repository(path: Path) -> bool:
    """
    Check if a path is a Git repository.

    Args:
        path: Path to check.

    Returns:
        True if path is a Git repository, False otherwise.
    """
    try:
        GitOperations(path)
        return True
    except GitError:
        return False


def find_git_root(path: Path) -> Optional[Path]:
    """
    Find the root of a Git repository.

    Args:
        path: Starting path to search from.

    Returns:
        Path to Git repository root, or None if not found.
    """
    current = path.absolute()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return None


# Alias for backward compatibility with tests
GitRepository = GitOperations
