
"""Directory scanning functionality for PTDU."""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from ptdu.cache import ScanCache


@dataclass
class ScanResult:
    """Result of scanning a single file or directory entry."""

    path: Path
    name: str
    size: int
    is_dir: bool
    error: Optional[str] = None


class Scanner:
    """Directory scanner using os.scandir() for optimal performance."""

    # Default patterns for system directories, version control, and cache folders
    DEFAULT_SKIP_PATTERNS: tuple[str, ...] = (
        "/proc",
        "/sys",
        "/dev",
        "/run",
        "/boot",
        ".git",
        ".svn",
        ".hg",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".egg-info",
        ".tox",
        "node_modules",
        ".aider*",
    )

    def __init__(
        self,
        skip_patterns: Optional[tuple[str, ...]] = None,
        follow_symlinks: bool = False,
        show_hidden: bool = True,
        exclude_patterns: Optional[tuple[str, ...]] = None,
        cache: Optional[ScanCache] = None,
    ) -> None:
        """Initialize scanner with configuration.

        Args:
            skip_patterns: Tuple of path patterns to skip (uses DEFAULT_SKIP_PATTERNS if None)
            follow_symlinks: Whether to follow symbolic links
            show_hidden: Whether to show hidden files (dotfiles)
            exclude_patterns: Additional patterns to exclude from scans
            cache: Optional ScanCache for caching results
        """
        self.skip_patterns: tuple[str, ...] = (
            skip_patterns or self.DEFAULT_SKIP_PATTERNS
        )
        self.follow_symlinks: bool = follow_symlinks
        self._show_hidden: bool = show_hidden
        self._exclude_patterns: tuple[str, ...] = exclude_patterns or ()
        self._cache: Optional[ScanCache] = cache
        self._use_cache: bool = cache is not None

    def should_skip(self, path: Path) -> bool:
        """Check if a path should be skipped based on skip patterns.

        Args:
            path: Path to check

        Returns:
            True if path should be skipped
        """
        path_str = str(path)
        name = path.name

        # Check each default skip pattern against the given path
        for pattern in self.skip_patterns:
            # Absolute patterns are matched against the beginning of the full path
            if pattern.startswith("/"):
                if path_str.startswith(pattern):
                    return True
            else:
                # Other patterns are checked against the name and full path
                if name == pattern or pattern in path_str:
                    return True

        # Check additional user-defined exclusion patterns
        for pattern in self._exclude_patterns:
            if pattern.startswith("/"):
                if path_str.startswith(pattern):
                    return True
            else:
                if name == pattern or pattern in path_str:
                    return True

        return False

    def set_exclude_patterns(self, patterns: tuple[str, ...]) -> None:
        """Set exclude patterns.

        Args:
            patterns: Patterns to exclude
        """
        self._exclude_patterns = patterns

    def add_exclude_pattern(self, pattern: str) -> None:
        """Add an exclude pattern.

        Args:
            pattern: Pattern to add
        """
        self._exclude_patterns = self._exclude_patterns + (pattern,)

    def set_cache(self, cache: Optional[ScanCache]) -> None:
        """Set cache for scan results.

        Args:
            cache: ScanCache instance or None
        """
        self._cache = cache
        self._use_cache = cache is not None

    def try_load_from_cache(self, path: Path) -> Optional[list[ScanResult]]:
        """Try to load scan results from cache.

        Args:
            path: Directory path

        Returns:
            List of ScanResult or None if not cached/invalid
        """
        # Skip cache lookup when caching is disabled or unavailable
        if not self._use_cache or self._cache is None:
            return None

        try:
            # Retrieve previously stored entries for this directory
            entries = self._cache.get(path)
            if entries is None:
                return None

            # Convert cached entries into ScanResult objects
            return [
                ScanResult(
                    path=Path(e.path),
                    name=e.name,
                    size=e.size,
                    is_dir=e.is_dir,
                )
                for e in entries
            ]
        except Exception:
            # Continue scanning normally if the cache cannot be read
            return None

    def store_in_cache(self, path: Path, results: list[ScanResult]) -> None:
        """Store scan results in cache.

        Args:
            path: Directory path
            results: Scan results to store
        """
        # Do nothing if caching is disabled or no cache is available
        if not self._use_cache or self._cache is None:
            return

        try:
            # Save the scan results for future use
            self._cache.store(path, results)
        except Exception:
            # Cache errors are non-critical
            pass

    def is_hidden(self, path: Path) -> bool:
        """Check if a path is a hidden file (starts with .).

        Args:
            path: Path to check

        Returns:
            True if path is hidden
        """
        return path.name.startswith(".")

    def set_show_hidden(self, show_hidden: bool) -> None:
        """Set whether to show hidden files.

        Args:
            show_hidden: True to show hidden files, False to hide them
        """
        self._show_hidden = show_hidden

    def should_show(self, path: Path) -> bool:
        """Check if a path should be shown based on filters.

        Args:
            path: Path to check

        Returns:
            True if path should be shown
        """
        # Hide dotfiles when the hidden-file option is disabled
        if not self._show_hidden and self.is_hidden(path):
            return False
        # Show the path only if it does not match any skip pattern
        return not self.should_skip(path)

    def scan_directory(
        self,
        path: Path,
        progress_callback: Optional[Callable[[ScanResult], None]] = None,
    ) -> list[ScanResult]:
        """Scan a directory and return results.

        Args:
            path: Directory path to scan
            progress_callback: Optional callback called for each entry found

        Returns:
            List of ScanResult objects
        """
        # Collect the results for all accessible entries in this directory
        results: list[ScanResult] = []

        # Stop if the directory matches an exclusion rule or should not be shown
        if self.should_skip(path) or not self.should_show(path):
            return results

        try:
            # Open the directory efficiently and iterate through its entries
            with os.scandir(path) as entries:
                for entry in entries:
                    # Ignore hidden entries when hidden-file display is disabled
                    if not self._show_hidden and entry.name.startswith("."):
                        continue
                    try:
                        # Process the entry and keep valid results
                        result = self._process_entry(entry)
                        if result is not None:
                            results.append(result)
                            # Notify the caller whenever an entry is processed
                            if progress_callback is not None:
                                progress_callback(result)
                    except (OSError, PermissionError) as e:
                        # Record inaccessible entries and continue scanning
                        error_result = ScanResult(
                            path=Path(entry.path),
                            name=entry.name,
                            size=0,
                            is_dir=False,
                            error=str(e),
                        )
                        results.append(error_result)
                        if progress_callback is not None:
                            progress_callback(error_result)

        except PermissionError:
            # Record that the directory cannot be accessed due to permissions
            results.append(
                ScanResult(
                    path=path,
                    name=path.name,
                    size=0,
                    is_dir=True,
                    error="Permission denied",
                )
            )


