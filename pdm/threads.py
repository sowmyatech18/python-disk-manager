```python
"""Threading components for background directory scanning."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from queue import Queue
from typing import Callable, Optional 

# Import DirNode to represent a directory or file in the directory tree.
from ptdu.models import DirNode

# Scanner performs the actual directory scanning.
# ScanResult represents the information collected about a scanned entry.
from ptdu.scanner import Scanner, ScanResult


# The dataclass automatically generates methods such as __init__.
# This class stores progress information while a scan is running.
@dataclass
class ScanProgress:
    """Progress update from a scan operation."""

    current_path: Path  # Directory currently being scanned
    items_scanned: int  # Number of entries scanned so far
    total_items: Optional[int] = None  # Total count, if known


# Represents one entry discovered during scanning.
# It allows the application to display results immediately,
# without waiting for the entire scan to finish.
@dataclass
class ScanEntry:
    """Single entry discovered during scan (for real-time updates)."""

    result: ScanResult  # Information about the discovered file or directory


# Represents a notification that the scan has finished successfully.
@dataclass
class ScanComplete:
    """Scan completion notification."""

    path: Path  # Path that was scanned
    results: list[ScanResult]  # All results collected by the scan
    total_size: int  # Combined size of all files found


# Represents a notification that an error occurred during scanning.
@dataclass
class ScanError:
    """Scan error notification."""

    path: Path  # Path where the scan was attempted
    error_message: str  # Description of the error


# Union type for scan messages
# A queue can contain any one of these four message types.
# This helps the main thread identify whether it received progress,
# a newly discovered entry, a completion notification, or an error.
ScanMessage = ScanProgress | ScanEntry | ScanComplete | ScanError


class ScanThread(threading.Thread):
    """Background thread for directory scanning."""

    def __init__(
        self,
        path: Path,
        scanner: Scanner,
        message_queue: Queue[ScanMessage],
        parent_node: Optional[DirNode] = None,
    ) -> None:
        """Initialize the scan thread.

        Args:
            path: Directory path to scan
            scanner: Scanner instance to use
            message_queue: Queue for sending progress/results back to main thread
            parent_node: Optional parent DirNode for tree structure
        """
        # Initialize the parent Thread class.
        # daemon=True allows the background thread to exit when
        # the main program exits.
        super().__init__(daemon=True)

        # Store the directory path that this thread must scan.
        self.path: Path = path

        # Store the scanner responsible for scanning the directory.
        self.scanner: Scanner = scanner

        # Store the queue used to send messages to the main thread.
        self.message_queue: Queue[ScanMessage] = message_queue

        # Store the optional parent node for the directory tree.
        self.parent_node: Optional[DirNode] = parent_node

        # Create an event that can be set to request the scan to stop.
        self._stop_event: threading.Event = threading.Event()

        # Count how many entries have been discovered so far.
        self._items_scanned: int = 0

        # Store the results received during the scan.
        self._results: list[ScanResult] = []

    def run(self) -> None:
        """Execute the scan operation in background."""
        # The run() method executes when the thread is started.
        # Exceptions are caught so that errors can be reported
        # to the main thread through the message queue.
        try:
            # If a stop request was already received, do not begin scanning.
            if self._stop_event.is_set():
                return

            # Send an initial progress update before scanning begins.
            # This lets the main thread know that the scan has started.
            self._send_progress()

            # Define a callback that is called whenever the scanner
            # discovers an entry.
            # This allows results to be sent to the main thread in real time.
            def on_entry_scanned(result: ScanResult) -> None:

                # Ignore new results if a stop request has been received.
                if self._stop_event.is_set():
                    return

                # Increase the number of entries scanned.
                self._items_scanned += 1

                # Save the discovered entry in the local results list.
                self._results.append(result)

                # Send the discovered entry immediately through the queue.
                # The main thread can use it to update the UI.
                self.message_queue.put(ScanEntry(result=result))

                # Send an updated progress notification.
                self._send_progress()

            # Perform a recursive scan of the directory.
            # The callback is invoked as entries are discovered.
            results = self.scanner.scan_recursive(
                self.path,
                progress_callback=on_entry_scanned,
            )

            # If scanning was cancelled, do not send a completion message.
            if self._stop_event.is_set():
                return

            # Calculate the total size of all files found.
            # Directories are excluded because their reported sizes
            # may not represent the sum of their contents.
            total_size = sum(r.size for r in results if not r.is_dir)

            # Notify the main thread that scanning has completed.
            # Include the scanned path, all results, and total file size.
            self.message_queue.put(
                ScanComplete(
                    path=self.path,
                    results=results,
                    total_size=total_size,
                )
            )

        except Exception as e:
            # If an exception occurs, send an error notification
            # instead of allowing the exception to go unreported.
            self.message_queue.put(
                ScanError(
                    path=self.path,
                    error_message=str(e),
                )
            )

    def _send_progress(self) -> None:
        """Send a progress update to the main thread."""
        # Create a progress message using the current path
        # and the number of entries scanned so far.
        self.message_queue.put(
            ScanProgress(
                current_path=self.path,
                items_scanned=self._items_scanned,
            )
        )

    def stop(self) -> None:
        """Request the scan to stop."""
        # Set the event to indicate that cancellation was requested.
        # The scanning code checks this event at appropriate points.
        self._stop_event.set()

    def is_stopped(self) -> bool:
        """Check if stop has been requested.

        Returns:
            True if stop has been requested
        """
        # Return True if the stop event has been set.
        return self._stop_event.is_set()


class ScanThreadManager:
    """Manages active scan threads and coordinates UI updates."""

    def __init__(self) -> None:
        """Initialize the scan manager."""
        # Store active scan threads using their directory paths as keys.
        self._active_threads: dict[Path, ScanThread] = {}

        # Create a shared queue for receiving messages from scan threads.
        self._message_queue: Queue[ScanMessage] = Queue()

        # A lock protects shared thread-tracking data from concurrent access.
        self._lock: threading.Lock = threading.Lock()

    def start_scan(
        self,
        path: Path,
        scanner: Scanner,
        parent_node: Optional[DirNode] = None,
    ) -> ScanThread:
        """Start a new scan thread.

        Args:
            path: Directory path to scan
            scanner: Scanner instance
            parent_node: Optional parent node

        Returns:
            The started ScanThread
        """
        # Acquire the lock before accessing the shared thread dictionary.
        with self._lock:

            # If a scan already exists for this path, request its cancellation.
            # This avoids intentionally running multiple scans for the same path.
            if path in self._active_threads:
                self._active_threads[path].stop()

            # Create a new background thread for the requested directory.
            thread = ScanThread(
                path=path,
                scanner=scanner,
                message_queue=self._message_queue,
                parent_node=parent_node,
            )

            # Register the new thread against its directory path.
            self._active_threads[path] = thread

            # Start the thread, which causes its run() method to execute.
            thread.start()

            # Return the thread so the caller can access or monitor it.
            return thread

    def get_messages(self) -> list[ScanMessage]:
        """Retrieve all pending messages from the queue.

        Returns:
            List of messages (non-blocking)
        """
        # Create a list to collect messages currently waiting in the queue.
        messages: list[ScanMessage] = []

        # Continue retrieving messages while the queue appears non-empty.
        while not self._message_queue.empty():
            try:
                # Retrieve the next message without waiting for a new one.
                msg = self._message_queue.get_nowait()

                # Add the retrieved message to the result list.
                messages.append(msg)

            except Exception:
                # Stop retrieving if an exception occurs.
                break

        # Return all messages successfully retrieved.
        return messages

    def stop_scan(self, path: Path) -> None:
        """Stop a specific scan.

        Args:
            path: Path of the scan to stop
        """
        # Lock the shared dictionary while looking up the requested thread.
        with self._lock:

            # If a thread exists for this path, request that it stop.
            if path in self._active_threads:
                self._active_threads[path].stop()

    def stop_all(self) -> None:
        """Stop all active scans."""
        # Lock the thread dictionary while iterating through it.
        with self._lock:

            # Request cancellation for every tracked scan thread.
            for thread in self._active_threads.values():
                thread.stop()

    def cleanup_finished(self) -> None:
        """Remove finished threads from tracking."""
        # Build a list of paths whose threads are no longer running.
        # is_alive() returns False when a thread has finished execution.
        finished = [
            path
            for path, thread in self._active_threads.items()
            if not thread.is_alive()
        ]

        # Remove finished threads from the tracking dictionary.
        for path in finished:
            del self._active_threads[path]

    def has_active_scans(self) -> bool:
        """Check if any scans are currently running.

        Returns:
            True if active scans exist
        """
        # Acquire the lock before inspecting shared thread information.
        with self._lock:

            # Remove threads that have already finished.
            self.cleanup_finished()

            # Return True if any threads remain in the dictionary.
            return len(self._active_threads) > 0

    def get_active_paths(self) -> list[Path]:
        """Get list of paths currently being scanned.

        Returns:
            List of paths
        """
        # Acquire the lock before reading the shared dictionary.
        with self._lock:

            # Remove completed threads before reporting active paths.
            self.cleanup_finished()

            # Return a list containing the paths of all tracked threads.
            return list(self._active_threads.keys())
```
