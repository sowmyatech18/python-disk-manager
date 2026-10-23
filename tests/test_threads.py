"""Tests for threads module."""

from pathlib import Path
from queue import Queue
from typing import cast

import pytest

from ptdu.models import DirNode
from ptdu.scanner import Scanner, ScanResult
from ptdu.threads import (
    ScanComplete,
    ScanError,
    ScanMessage,
    ScanProgress,
    ScanThread,
    ScanThreadManager,
)


class TestScanProgress:
    """Tests for ScanProgress dataclass."""

    def test_create_scan_progress(self) -> None:
        """Test creating a ScanProgress."""
        # Create a ScanProgress object with the current path and scan counts.
        progress = ScanProgress(
            current_path=Path("/test"),
            items_scanned=5,
            total_items=10,
        )

        # Check that each attribute contains the expected value.
        assert progress.current_path == Path("/test")
        assert progress.items_scanned == 5
        assert progress.total_items == 10


class TestScanComplete:
    """Tests for ScanComplete dataclass."""

    def test_create_scan_complete(self) -> None:
        """Test creating a ScanComplete."""
        # Create a sample scan result for a file.
        results = [
            ScanResult(
                path=Path("/test/file.txt"), name="file.txt", size=100, is_dir=False
            )
        ]

        # Create a ScanComplete object containing the scan results and total size.
        complete = ScanComplete(
            path=Path("/test"),
            results=results,
            total_size=100,
        )

        # Verify that the completion object stores the expected values.
        assert complete.path == Path("/test")
        assert complete.results == results
        assert complete.total_size == 100


class TestScanError:
    """Tests for ScanError dataclass."""

    def test_create_scan_error(self) -> None:
        """Test creating a ScanError."""
        # Create a ScanError object with a path and an error message.
        error = ScanError(
            path=Path("/test"),
            error_message="Permission denied",
        )

        # Check that the error details were stored correctly.
        assert error.path == Path("/test")
        assert error.error_message == "Permission denied"


class TestScanThread:
    """Tests for ScanThread class."""

    def test_thread_initialization(self) -> None:
        """Test ScanThread initialization."""
        # Create a queue to receive messages from the scanning thread.
        queue: Queue[ScanMessage] = Queue()

        # Create a Scanner instance and the path to scan.
        scanner = Scanner()
        path = Path("/tmp")

        # Initialize the scanning thread with the required objects.
        thread = ScanThread(
            path=path,
            scanner=scanner,
            message_queue=queue,
        )

        # Verify that the thread stores the correct initialization values.
        assert thread.path == path
        assert thread.scanner == scanner
        assert thread.message_queue == queue

        # No parent node is provided, so it should be None.
        assert thread.parent_node is None

        # The thread should not be stopped immediately after initialization.
        assert thread.is_stopped() is False

    def test_thread_with_parent_node(self) -> None:
        """Test ScanThread with parent node."""
        # Create a queue for thread messages.
        queue: Queue[ScanMessage] = Queue()

        # Create a scanner instance.
        scanner = Scanner()

        # Create a directory node to represent the parent directory.
        parent = DirNode(path=Path("/parent"), name="parent", is_dir=True)

        # Initialize the thread with its parent directory node.
        thread = ScanThread(
            path=Path("/parent/child"),
            scanner=scanner,
            message_queue=queue,
            parent_node=parent,
        )

        # Confirm that the parent node is assigned correctly.
        assert thread.parent_node == parent

    def test_stop_request(self) -> None:
        """Test stop request sets stop event."""
        # Create the message queue and scanner for the thread.
        queue: Queue[ScanMessage] = Queue()
        scanner = Scanner()

        # Initialize the thread.
        thread = ScanThread(
            path=Path("/tmp"),
            scanner=scanner,
            message_queue=queue,
        )

        # Initially, the thread should not be stopped.
        assert thread.is_stopped() is False

        # Request the thread to stop.
        thread.stop()

        # Verify that the stop request was recorded.
        assert thread.is_stopped() is True


class TestScanThreadManager:
    """Tests for ScanThreadManager class."""

    def test_manager_initialization(self) -> None:
        """Test ScanThreadManager initialization."""
        # Import ScanThreadManager and create an instance.
        from ptdu.threads import ScanThreadManager

        manager = ScanThreadManager()

        # Verify that the manager object was created successfully.
        assert manager is not None
