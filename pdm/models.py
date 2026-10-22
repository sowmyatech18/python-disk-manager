
"""Data models for PTDU directory structure."""

from __future__ import annotations

from pathlib import Path
from typing import Optional


class DirNode:
    """Represents a file or directory node in the tree structure."""

    def __init__(
        self,
        path: Path,
        name: str,
        is_dir: bool,
        parent: Optional[DirNode] = None,
    ) -> None:
        """Initialize a directory node.

        Args:
            path: Full filesystem path
            name: Display name
            is_dir: Whether this is a directory
            parent: Reference to parent node (None for root)
        """
        self.path: Path = path
        self.name: str = name
        self.size: int = 0
        self.children: dict[str, DirNode] = {}
        self.parent: Optional[DirNode] = parent
        self.is_dir: bool = is_dir
        self.is_expanded: bool = False
        self._is_loaded: bool = False

    def get_size(self) -> int:
        """Get the total size of this node.

        For directories, returns the cached size.
        For files, returns the file size.

        Returns:
            Size in bytes
        """
        return self.size

    def add_child(self, node: DirNode) -> None:
        """Add a child node to this directory.

        Args:
            node: The child node to add

        Raises:
            ValueError: If this node is not a directory
        """
        if not self.is_dir:
            raise ValueError(f"Cannot add child to file: {self.name}")

        self.children[node.name] = node
        node.parent = self

    def remove_child(self, name: str) -> Optional[DirNode]:
        """Remove a child node by name.

        Args:
            name: Name of the child to remove

        Returns:
            The removed node or None if not found

        Raises:
            ValueError: If this node is not a directory
        """
        if not self.is_dir:
            raise ValueError(f"Cannot remove child from file: {self.name}")

        node = self.children.pop(name, None)
        if node is not None:
            node.parent = None
        return node

    def get_child(self, name: str) -> Optional[DirNode]:
        """Get a child node by name.

        Args:
            name: Name of the child to get

        Returns:
            The child node or None if not found
        """
        return self.children.get(name)

    def set_size(self, size: int) -> None:
        """Set the size of this node and propagate to parents.

        Args:
            size: New size in bytes
        """
        old_size = self.size
        self.size = size


