```python
"""Performance optimizations for large directory handling."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Optional

# TYPE_CHECKING ensures that DirNode is imported only for type checking.
# This avoids an unnecessary runtime import.
if TYPE_CHECKING:
    from ptdu.models import DirNode


# A dataclass automatically provides methods like __init__ and __repr__.
# This class stores the range of items that should currently be displayed.
@dataclass
class VirtualRange:
    """Represents a visible range for virtual scrolling."""

    start: int  # Index of the first visible item
    end: int    # Index just after the last visible item
    total: int  # Total number of items available


class VirtualScroller:
    """Manages virtual scrolling for large directories."""

    # Default number of items to render
    DEFAULT_WINDOW_SIZE: int = 100

    # Buffer size for smooth scrolling
    BUFFER_SIZE: int = 20

    def __init__(
        self, total_items: int = 0, window_size: int = DEFAULT_WINDOW_SIZE
    ) -> None:
        """Initialize virtual scroller.

        Args:
            total_items: Total number of items
            window_size: Number of items to render at once
        """
        # Store the total number of items.
        self._total: int = total_items

        # Store how many items should be visible at a time.
        self._window_size: int = window_size

        # Initially, scrolling starts from the first item (index 0).
        self._current_start: int = 0

    def set_total(self, total: int) -> None:
        """Update total item count.

        Args:
            total: New total number of items
        """
        # Update the total number of available items.
        self._total = total

        # Ensure the current starting position is still valid.
        self._clamp_start()

    def get_visible_range(self) -> VirtualRange:
        """Get the currently visible range.

        Returns:
            VirtualRange with start, end, and total
        """
        # Calculate the ending index without exceeding the total item count.
        end = min(self._current_start + self._window_size, self._total)

        # Return the starting index, ending index, and total item count.
        return VirtualRange(
            start=self._current_start,
            end=end,
            total=self._total,
        )

    def scroll_to(self, position: int) -> VirtualRange:
        """Scroll to a specific position.

        Args:
            position: Target position (0-based)

        Returns:
            New visible range
        """
        # Move to the requested position while keeping it non-negative
        # and within the available item indices.
        self._current_start = max(0, min(position, self._total - 1))

        # Adjust the position so the visible window stays within valid bounds.
        self._clamp_start()

        # Return the updated visible range.
        return self.get_visible_range()

    def scroll_down(self, amount: int = 1) -> VirtualRange:
        """Scroll down by amount.

        Args:
            amount: Number of items to scroll

        Returns:
            New visible range
        """
        # Increase the starting index to move down through the items.
        self._current_start += amount

        # Prevent scrolling beyond the valid range.
        self._clamp_start()

        # Return the new visible range.
        return self.get_visible_range()

    def scroll_up(self, amount: int = 1) -> VirtualRange:
        """Scroll up by amount.

        Args:
            amount: Number of items to scroll

        Returns:
            New visible range
        """
        # Decrease the starting index to move up through the items.
        self._current_start -= amount

        # Prevent the starting index from becoming negative.
        self._clamp_start()

        # Return the new visible range.
        return self.get_visible_range()

    def page_down(self) -> VirtualRange:
        """Scroll down by one page.

        Returns:
            New visible range
        """
        # Move down by the size of one complete visible window.
        return self.scroll_down(self._window_size)

    def page_up(self) -> VirtualRange:
        """Scroll up by one page.

        Returns:
            New visible range
        """
        # Move up by the size of one complete visible window.
        return self.scroll_up(self._window_size)

    def _clamp_start(self) -> None:
        """Clamp start position to valid range."""
        # Find the largest starting index that allows a full window
        # to fit within the total number of items.
        max_start = max(0, self._total - self._window_size)

        # Keep the starting index between 0 and max_start.
        self._current_start = max(0, min(self._current_start, max_start))

    def is_visible(self, index: int) -> bool:
        """Check if an index is currently visible.

        Args:
            index: Item index to check

        Returns:
            True if visible
        """
        # Get the current visible range.
        visible = self.get_visible_range()

        # An index is visible if it is at least start
        # and strictly less than end.
        return visible.start <= index < visible.end

    def get_item_index_at(self, y_position: int, item_height: int) -> int:
        """Get item index at a Y position.

        Args:
            y_position: Y coordinate
            item_height: Height of each item in pixels

        Returns:
            Item index
        """
        # Divide the vertical coordinate by the item height to find
        # the offset from the first visible item.
        # Add the current starting index to get the overall item index.
        return self._current_start + (y_position // item_height)


class MemoryOptimizer:
    """Optimizes memory usage for large directory trees."""

    # Maximum children to keep in memory per directory
    MAX_CACHED_CHILDREN: int = 1000

    # Maximum depth for initial scan
    MAX_INITIAL_DEPTH: int = 3

    def __init__(self) -> None:
        """Initialize memory optimizer."""
        # Store paths of nodes whose children have been unloaded.
        self._unloaded_nodes: set[str] = set()

        # Track the greatest depth reached during scanning.
        self._max_depth_reached: int = 0

    def should_unload_children(self, node: DirNode) -> bool:
        """Check if a node's children should be unloaded.

        Args:
            node: Directory node to check

        Returns:
            True if children should be unloaded
        """
        # Files do not contain directory children to unload.
        if not node.is_dir:
            return False

        # If the directory contains too many children,
        # recommend unloading them to reduce memory usage.
        if len(node.children) > self.MAX_CACHED_CHILDREN:
            return True

        # The number of children is within the allowed limit.
        return False

    def unload_children(self, node: DirNode) -> list[str]:
        """Unload children from memory, returning names of unloaded children.

        Args:
            node: Directory node to unload

        Returns:
            List of unloaded child names
        """
        # A file has no directory children to unload.
        if not node.is_dir:
            return []

        # Create a list to store the names of unloaded children.
        unloaded: list[str] = []

        # Visit each child in the directory.
        for name, child in node.children.items():

            # Record the child's path so we can track the unloaded node.
            self._unloaded_nodes.add(str(child.path))

            # Save the child's name in the list being returned.
            unloaded.append(name)

        # Remove all child references from memory.
        # The directory node itself is preserved.
        node.children.clear()

        # Mark the directory as not currently loaded.
        node._is_loaded = False

        # Return the names of the children that were unloaded.
        return unloaded

    def reload_children(
        self,
        node: DirNode,
        loader: Callable[[], list[DirNode]],
    ) -> None:
        """Reload children using a loader function.

        Args:
            node: Directory node to reload
            loader: Function that returns list of child nodes
        """
        # Only directories can have their children reloaded.
        if not node.is_dir:
            return

        # Call the loader function to retrieve the child nodes.
        children = loader()

        # Add every loaded child back to the directory node.
        for child in children:
            node.add_child(child)

        # Mark the directory as loaded after adding its children.
        node._is_loaded = True

        # Remove the directory's own path from the unloaded-node set.
        self._unloaded_nodes.discard(str(node.path))

    def get_initial_scan_depth(self, estimated_total_items: int) -> int:
        """Get recommended initial scan depth based on estimated size.

        Args:
            estimated_total_items: Estimated number of items

        Returns:
            Recommended scan depth
        """
        # For extremely large directory structures, scan fewer levels
        # initially to reduce processing time and memory usage.
        if estimated_total_items > 100000:
            return 2

        # For moderately large structures, use a depth of 3.
        elif estimated_total_items > 10000:
            return 3

        # For smaller structures, use the default initial scan depth.
        else:
            return self.MAX_INITIAL_DEPTH

    def limit_recursion_depth(
        self, current_depth: int, max_depth: Optional[int
