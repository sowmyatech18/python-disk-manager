
"""Tests for the scanner module."""

# Import operating-system tools for reading directory entries
import os

# Create temporary directories for testing without changing real files
import tempfile

# Work with filesystem paths
from pathlib import Path

# Testing framework used to run these test cases
import pytest

# Import the scanner and the result structure being tested
from ptdu.scanner import Scanner, ScanResult


class TestScanResult:
    """Test the ScanResult data structure."""

    def test_create_scan_result(self) -> None:
        """Check that a scan result stores the correct information."""
        result = ScanResult(
            path=Path("/test/file.txt"),
            name="file.txt",
            size=1024,
            is_dir=False,
        )

        # Verify that every field contains the expected value
        assert result.path == Path("/test/file.txt")
        assert result.name == "file.txt"
        assert result.size == 1024
        assert result.is_dir is False
        assert result.error is None

    def test_create_scan_result_with_error(self) -> None:
        """Check that an error message can be stored in a result."""
        result = ScanResult(
            path=Path("/test"),
            name="test",
            size=0,
            is_dir=True,
            error="Permission denied",
        )

        # Confirm that the error message is preserved
        assert result.error == "Permission denied"


class TestScannerInitialization:
    """Test the Scanner's default and custom settings."""

    def test_default_initialization(self) -> None:
        """Check the default scanner configuration."""
        scanner = Scanner()

        # By default, symbolic links are not followed
        assert scanner.follow_symlinks is False

        # Default exclusion patterns should be available
        assert len(scanner.skip_patterns) > 0
        assert "/proc" in scanner.skip_patterns
        assert ".git" in scanner.skip_patterns

    def test_custom_skip_patterns(self) -> None:
        """Check whether custom exclusion patterns are accepted."""
        patterns = (".custom", "temp")
        scanner = Scanner(skip_patterns=patterns)

        # The scanner should use the supplied patterns
        assert scanner.skip_patterns == patterns

    def test_follow_symlinks_enabled(self) -> None:
        """Check whether symbolic-link following can be enabled."""
        scanner = Scanner(follow_symlinks=True)

        assert scanner.follow_symlinks is True


class TestScannerShouldSkip:
    """Test the rules used to exclude paths from scanning."""

    def test_skip_absolute_pattern(self) -> None:
        """Check that protected system paths are excluded."""
        scanner = Scanner()

        assert scanner.should_skip(Path("/proc")) is True
        assert scanner.should_skip(Path("/proc/123")) is True
        assert scanner.should_skip(Path("/sys/devices")) is True

    def test_skip_name_pattern(self) -> None:
        """Check exclusion based on directory names."""
        scanner = Scanner()

        assert scanner.should_skip(Path("/path/.git")) is True
        assert scanner.should_skip(Path("/path/__pycache__")) is True

    def test_do_not_skip_regular_path(self) -> None:
        """Check that ordinary paths are allowed."""
        scanner = Scanner()

        assert scanner.should_skip(Path("/home/user")) is False
        assert scanner.should_skip(Path("/tmp/test.txt")) is False

    def test_custom_skip_pattern(self) -> None:
        """Check that a custom pattern excludes matching paths."""
        scanner = Scanner(skip_patterns=("node_modules",))

        assert scanner.should_skip(Path("/project/node_modules")) is True
        assert scanner.should_skip(Path("/project/node_modules/package")) is True
        assert scanner.should_skip(Path("/project/src")) is False


class TestScannerScanDirectory:
    """Test scanning the immediate contents of a directory."""

    def test_scan_empty_directory(self) -> None:
        """An empty directory should return an empty list."""
        scanner = Scanner()

        # Create a temporary directory that is automatically cleaned up
        with tempfile.TemporaryDirectory() as tmpdir:
            results = scanner.scan_directory(Path(tmpdir))

            assert results == []

    def test_scan_directory_with_files(self) -> None:
        """Check file names, sizes, and types."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create two files with known contents and sizes
            (Path(tmpdir) / "file1.txt").write_text("content1")
            (Path(tmpdir) / "file2.txt").write_text("content2" * 100)

            results = scanner.scan_directory(Path(tmpdir))

            # Both files should be returned
            assert len(results) == 2

            # Collect file names into a set for comparison
            names = {r.name for r in results}
            assert names == {"file1.txt", "file2.txt"}

            # Find each file's result to check its size
            file1 = next(r for r in results if r.name == "file1.txt")
            file2 = next(r for r in results if r.name == "file2.txt")

            assert file1.size == 8
            assert file2.size == 800
            assert file1.is_dir is False
            assert file2.is_dir is False

    def test_scan_directory_with_subdirectories(self) -> None:
        """Check how a direct scan handles a child directory."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a subdirectory containing a file
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            (subdir / "file.txt").write_text("content")

            results = scanner.scan_directory(Path(tmpdir))

            # The direct scan should return the subdirectory itself
            assert len(results) == 1

            subdir_result = results[0]
            assert subdir_result.name == "subdir"
            assert subdir_result.is_dir is True

            # Directory size starts at zero in this scan result
            assert subdir_result.size == 0

    def test_scan_skips_patterns(self) -> None:
        """Check that excluded entries are not returned."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create one regular file and one excluded directory
            (Path(tmpdir) / "file.txt").write_text("content")
            git_dir = Path(tmpdir) / ".git"
            git_dir.mkdir()
            (git_dir / "config").write_text("config")

            results = scanner.scan_directory(Path(tmpdir))

            # Only the regular file should be included
            assert len(results) == 1
            assert results[0].name == "file.txt"

    def test_scan_nonexistent_directory(self) -> None:
        """Check that a missing directory produces an error result."""
        scanner = Scanner()

        results = scanner.scan_directory(Path("/nonexistent/path"))

        assert len(results) == 1
        assert results[0].error is not None

        # Accept either of the expected missing-path error messages
        assert (
            "not found" in results[0].error.lower()
            or "directory not found" in results[0].error.lower()
        )

    def test_progress_callback(self) -> None:
        """Check that the progress callback receives each entry."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create two files for the scanner to discover
            (Path(tmpdir) / "file1.txt").write_text("content1")
            (Path(tmpdir) / "file2.txt").write_text("content2")

            # Store every result received by the callback
            callback_results: list[ScanResult] = []

            def callback(result: ScanResult) -> None:
                callback_results.append(result)

            # Pass the callback to the directory scanner
            scanner.scan_directory(Path(tmpdir), progress_callback=callback)

            assert len(callback_results) == 2


class TestScannerProcessEntry:
    """Test processing one filesystem entry at a time."""

    def test_process_file_entry(self) -> None:
        """Check how a file entry is converted into a scan result."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file containing 12 characters
            file_path = Path(tmpdir) / "test.txt"
            file_path.write_text("test content")

            # Obtain the directory entry using os.scandir()
            with os.scandir(tmpdir) as entries:
                entry = next(entries)
                result = scanner._process_entry(entry)

                assert result is not None
                assert result.name == "test.txt"
                assert result.size == 12
                assert result.is_dir is False

    def test_process_directory_entry(self) -> None:
        """Check how a directory entry is processed."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a child directory
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()

            with os.scandir(tmpdir) as entries:
                entry = next(entries)
                result = scanner._process_entry(entry)

                assert result is not None
                assert result.name == "subdir"
                assert result.is_dir is True
                assert result.size == 0

    def test_process_skipped_entry(self) -> None:
        """A skipped entry should return None."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a directory that the scanner excludes
            git_dir = Path(tmpdir) / ".git"
            git_dir.mkdir()

            with os.scandir(tmpdir) as entries:
                entry = next(entries)
                result = scanner._process_entry(entry)

                assert result is None

    def test_process_broken_symlink(self) -> None:
        """Check that a broken symbolic link is handled safely."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a link pointing to a path that does not exist
            link_path = Path(tmpdir) / "broken_link"
            link_path.symlink_to("/nonexistent/path")

            with os.scandir(tmpdir) as entries:
                entry = next(entries)
                result = scanner._process_entry(entry)

                # Processing should return a result rather than crash
                assert result is not None
                assert result.error is not None or result.size == 0


class TestScannerScanRecursive:
    """Test scanning through nested directories."""

    def test_scan_recursive_depth_0(self) -> None:
        """Check behavior when maximum depth is zero."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a child directory and a file inside it
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            (subdir / "file.txt").write_text("content")

            results = scanner.scan_recursive(Path(tmpdir), max_depth=0)

            # No child entries should be returned at depth zero
            assert len(results) == 0

    def test_scan_recursive_depth_1(self) -> None:
        """Check that depth one returns only immediate entries."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file and a directory containing another file
            (Path(tmpdir) / "file1.txt").write_text("content")
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            (subdir / "file2.txt").write_text("content")

            results = scanner.scan_recursive(Path(tmpdir), max_depth=1)

            # The nested file should not appear at this depth
            assert len(results) == 2
            names = {r.name for r in results}
            assert names == {"file1.txt", "subdir"}

    def test_scan_recursive_unlimited(self) -> None:
        """Check that unlimited scanning includes nested entries."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Build a two-level directory structure
            (Path(tmpdir) / "file1.txt").write_text("content")
            subdir1 = Path(tmpdir) / "level1"
            subdir1.mkdir()
            (subdir1 / "file2.txt").write_text("content")
            subdir2 = subdir1 / "level2"
            subdir2.mkdir()
            (subdir2 / "file3.txt").write_text("content")

            results = scanner.scan_recursive(Path(tmpdir))

            # Confirm that entries from all levels are included
            names = {r.name for r in results}
            assert "file1.txt" in names
            assert "file2.txt" in names
            assert "file3.txt" in names
            assert "level1" in names
            assert "level2" in names

    def test_scan_recursive_skips_patterns(self) -> None:
        """Check that excluded directories are skipped recursively."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a normal file and an excluded directory
            (Path(tmpdir) / "file1.txt").write_text("content")
            git_dir = Path(tmpdir) / ".git"
            git_dir.mkdir()
            (git_dir / "config").write_text("config")

            results = scanner.scan_recursive(Path(tmpdir))

            names = {r.name for r in results}
            assert "file1.txt" in names
            assert ".git" not in names
            assert "config" not in names


class TestScannerGetDirectorySize:
    """Test calculation of directory sizes."""

    def test_get_directory_size_empty(self) -> None:
        """An empty directory should have size zero."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            size = scanner.get_directory_size(Path(tmpdir))

            assert size == 0

    def test_get_directory_size_with_files(self) -> None:
        """Check that file sizes are added correctly."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files with known sizes: 8 bytes and 80 bytes
            (Path(tmpdir) / "file1.txt").write_text("content1")
            (Path(tmpdir) / "file2.txt").write_text("content2" * 10)

            size = scanner.get_directory_size(Path(tmpdir))

            # Total should be 8 + 80 = 88 bytes
            assert size == 88

    def test_get_directory_size_recursive(self) -> None:
        """Check that nested files are included in the total size."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create one file in the main directory
            (Path(tmpdir) / "file1.txt").write_text("content1")

            # Create a nested directory containing another file
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            (subdir / "file2.txt").write_text("content2")

            size = scanner.get_directory_size(Path(tmpdir))

            # Each file contains 8 bytes, so the total is 16
            assert size == 16

    def test_get_directory_size_skips_patterns(self) -> None:
        """Check that excluded directories do not add to the total."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a regular file and a file inside an excluded directory
            (Path(tmpdir) / "file1.txt").write_text("content1")
            git_dir = Path(tmpdir) / ".git"
            git_dir.mkdir()
            (git_dir / "config").write_text("large content" * 100)

            size = scanner.get_directory_size(Path(tmpdir))

            # Only the regular file should contribute to the total
            assert size == 8
