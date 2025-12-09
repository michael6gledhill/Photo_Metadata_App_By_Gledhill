#!/usr/bin/env python3
"""
Update checker for Photo Metadata Editor.
Checks for updates from GitHub and handles app updates.
"""

import json
import subprocess
import sys
import logging
from pathlib import Path
from typing import Optional, Tuple
from urllib.request import urlopen
from urllib.error import URLError
import threading

logger = logging.getLogger(__name__)

GITHUB_REPO = "michael6gledhill/Photo_Metadata_App_By_Gledhill"
RELEASES_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
GITHUB_PAGES_URL = "https://michael6gledhill.github.io/Photo_Metadata_App_By_Gledhill/"


class UpdateChecker:
    """Checks for app updates and manages the update process."""
    
    def __init__(self):
        self.current_version = self.get_current_version()
        self.latest_version = None
        self.update_available = False
        
    @staticmethod
    def get_current_version() -> str:
        """Get the current app version from package metadata."""
        # Read from a simple version.txt file or return a default
        version_file = Path(__file__).parent / "version.txt"
        if version_file.exists():
            return version_file.read_text().strip()
        return "1.0.0"
    
    @staticmethod
    def save_current_version(version: str):
        """Save the current version to a file."""
        version_file = Path(__file__).parent / "version.txt"
        version_file.write_text(version)
    
    def check_for_updates(self) -> Tuple[bool, Optional[str]]:
        """
        Check GitHub for the latest version.
        Returns: (update_available, latest_version)
        """
        try:
            with urlopen(RELEASES_API_URL, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                self.latest_version = data['tag_name'].lstrip('v')
                
                # Compare versions (simple comparison)
                if self._compare_versions(self.latest_version, self.current_version) > 0:
                    self.update_available = True
                    logger.info(f"Update available: {self.latest_version}")
                    return True, self.latest_version
                else:
                    logger.info(f"No update available. Current: {self.current_version}")
                    return False, None
        except (URLError, json.JSONDecodeError, KeyError, Exception) as e:
            logger.warning(f"Failed to check for updates: {e}")
            return False, None
    
    @staticmethod
    def _compare_versions(version1: str, version2: str) -> int:
        """
        Compare two version strings.
        Returns: 1 if version1 > version2, -1 if version1 < version2, 0 if equal
        """
        try:
            v1_parts = [int(x) for x in version1.split('.')]
            v2_parts = [int(x) for x in version2.split('.')]
            
            # Pad shorter version with zeros
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts += [0] * (max_len - len(v1_parts))
            v2_parts += [0] * (max_len - len(v2_parts))
            
            for v1, v2 in zip(v1_parts, v2_parts):
                if v1 > v2:
                    return 1
                elif v1 < v2:
                    return -1
            return 0
        except (ValueError, AttributeError):
            return 0
    
    def perform_update(self) -> bool:
        """
        Perform the update by pulling the latest code and rebuilding.
        Returns: True if successful, False otherwise
        """
        try:
            repo_path = Path(__file__).parent
            
            logger.info("Fetching latest code...")
            # Pull latest from GitHub
            subprocess.run(
                ["git", "pull", "origin", "main"],
                cwd=repo_path,
                check=True,
                capture_output=True
            )
            
            logger.info("Installing dependencies...")
            # Install/update requirements
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-q", "-r", "requirements.txt"],
                cwd=repo_path,
                check=True,
                capture_output=True
            )
            
            # Save the new version
            if self.latest_version:
                self.save_current_version(self.latest_version)
                self.current_version = self.latest_version
            
            logger.info("Update completed successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Update failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during update: {e}")
            return False
    
    @staticmethod
    def get_github_pages_url() -> str:
        """Get the GitHub Pages documentation URL."""
        return GITHUB_PAGES_URL
    
    def check_for_updates_async(self, callback) -> None:
        """Check for updates in a separate thread."""
        def check():
            result = self.check_for_updates()
            callback(result)
        
        thread = threading.Thread(target=check, daemon=True)
        thread.start()
