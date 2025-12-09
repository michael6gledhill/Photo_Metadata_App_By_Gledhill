#!/usr/bin/env python3
"""
Update checker for Photo Metadata Editor.
Checks for updates from GitHub and handles app updates.
"""

import json
import subprocess
import sys
import logging
import ssl
from pathlib import Path
from typing import Optional, Tuple
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import threading

try:
    import certifi  # type: ignore
except ImportError:  # certifi is optional; we fall back to system certs
    certifi = None

logger = logging.getLogger(__name__)

GITHUB_REPO = "michael6gledhill/Photo_Metadata_App_By_Gledhill"
RELEASES_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
RAW_VERSION_URL = "https://raw.githubusercontent.com/michael6gledhill/Photo_Metadata_App_By_Gledhill/main/version.txt"
GITHUB_PAGES_URL = "https://michael6gledhill.github.io/Photo_Metadata_App_By_Gledhill/"


class UpdateChecker:
    """Checks for app updates and manages the update process."""
    
    def __init__(self):
        self.current_version = self.get_current_version()
        self.latest_version = None
        self.update_available = False
        self.last_error: Optional[str] = None
        
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
        # Reset state before each check so stale flags don't persist
        self.last_error = None
        self.update_available = False
        self.latest_version = None
        candidates = []

        release_version = self._fetch_latest_release_version()
        if release_version:
            candidates.append(("release", release_version))

        raw_version = self._fetch_latest_raw_version()
        if raw_version:
            candidates.append(("raw", raw_version))

        if not candidates:
            if not self.last_error:
                self.last_error = "No version sources returned a value"
            return False, None

        latest_source, latest_version = candidates[0]
        for source, version in candidates[1:]:
            if self._compare_versions(version, latest_version) > 0:
                latest_source, latest_version = source, version

        self.latest_version = latest_version

        if self._compare_versions(self.latest_version, self.current_version) > 0:
            self.update_available = True
            logger.info(f"Update available from {latest_source}: {self.latest_version}")
            return True, self.latest_version

        logger.info(f"No update available. Current: {self.current_version}, Latest: {self.latest_version}")
        return False, self.latest_version

    def _fetch_latest_release_version(self) -> Optional[str]:
        req = Request(RELEASES_API_URL, headers={"User-Agent": "PhotoMetadataEditor-Updater"})
        try:
            with urlopen(req, timeout=6, context=self._get_ssl_context()) as response:
                data = json.loads(response.read().decode('utf-8'))
                return data.get('tag_name', '').lstrip('v') or None
        except URLError as e:
            # Retry once with insecure SSL if certs are broken locally
            if isinstance(getattr(e, "reason", None), ssl.SSLError):
                self.last_error = f"Releases API SSL failed: {e}"  # keep the real cause
                logger.warning(self.last_error)
                try:
                    with urlopen(req, timeout=6, context=self._get_ssl_context(insecure=True)) as response:
                        data = json.loads(response.read().decode('utf-8'))
                        logger.warning("Releases API succeeded with insecure SSL fallback; please fix system certificates.")
                        return data.get('tag_name', '').lstrip('v') or None
                except Exception as inner:
                    self.last_error = f"Releases API insecure fallback failed: {inner}"
                    logger.warning(self.last_error)
                    return None
            self.last_error = f"Releases API failed: {e}"
            logger.warning(self.last_error)
            return None
        except (HTTPError, json.JSONDecodeError, KeyError) as e:
            self.last_error = f"Releases API failed: {e}"
            logger.warning(self.last_error)
            return None

    def _fetch_latest_raw_version(self) -> Optional[str]:
        req = Request(RAW_VERSION_URL, headers={"User-Agent": "PhotoMetadataEditor-Updater"})
        try:
            with urlopen(req, timeout=6, context=self._get_ssl_context()) as response:
                text = response.read().decode('utf-8').strip()
                return text or None
        except URLError as e:
            if isinstance(getattr(e, "reason", None), ssl.SSLError):
                self.last_error = f"Raw version SSL failed: {e}"
                logger.warning(self.last_error)
                try:
                    with urlopen(req, timeout=6, context=self._get_ssl_context(insecure=True)) as response:
                        text = response.read().decode('utf-8').strip()
                        logger.warning("Raw version fetch succeeded with insecure SSL fallback; please fix system certificates.")
                        return text or None
                except Exception as inner:
                    self.last_error = f"Raw version insecure fallback failed: {inner}"
                    logger.warning(self.last_error)
                    return None
            self.last_error = f"Raw version fetch failed: {e}"
            logger.warning(self.last_error)
            return None
        except Exception as e:
            self.last_error = f"Raw version fetch failed: {e}"
            logger.warning(self.last_error)
            return None

    @staticmethod
    def _get_ssl_context(insecure: bool = False):
        """Return an SSL context that trusts certifi if available, or optionally disable verification."""
        if insecure:
            return ssl._create_unverified_context()
        ctx = ssl.create_default_context()
        if certifi:
            try:
                ctx.load_verify_locations(certifi.where())
            except Exception:
                # If loading certifi fails, continue with default context
                pass
        return ctx
    
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
            try:
                result = self.check_for_updates()
                callback(result)
            except Exception as e:
                logger.error(f"Async update check failed: {e}")
                callback((False, None))
        
        thread = threading.Thread(target=check, daemon=True)
        thread.start()
