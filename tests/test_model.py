"""Tests for PTDU models."""

from pathlib import Path

import pytest

from ptdu.models import DirNode


class TestDirNode:
    """Tests for DirNode class."""

    def test_create_file_node(self) -> None:
        """Test creating a file node."""
        path = Path("/home/user/file.txt")
        node = DirNode(path=path, name="file.txt", is_dir=False)

        assert node.path == path
        assert node.name == "file.txt"
        assert node.is_dir is False
        assert node.size == 0
        assert node.parent is None
        assert node.is_expanded is False
        assert node.is_loaded() is False

    def test_create_directory_node(self) -> None:
        """Test creating a directory node."""
        path = Path("/home/user/docs")
        node = DirNode(path=path, name="docs", is_dir=True)

        assert node.path == path
        assert node.name == "docs"
        assert node.is_dir is True
        assert node.children == {}

    def test_add_child_to_directory(self) -> None:
        """Test adding a child to a directory."""
        parent = DirNode(path=Path("/parent"), name="parent", is_dir=True)
        child = DirNode(path=Path("/parent/child"), name="child", is_dir=True)

        parent.add_child(child)

        assert "child" in parent.children
        assert parent.children["child"] == child
        assert child.parent == parent

    def test_add_child_to_file_raises(self) -> None:
        """Test that adding a child to a file raises ValueError."""
        file_node = DirNode(path=Path("/file.txt"), name="file.txt", is_dir=False)
        child = DirNode(path=Path("/file.txt/child"), name="child", is_dir=True)

        with pytest.raises(ValueError):
            file_node.add_child(child)

    def test_remove_child(self) -> None:
        """Test removing a child from a directory."""
        parent = DirNode(path=Path("/parent"), name="parent", is_dir=True)
        child = DirNode(path=Path("/parent/child"), name="child", is_dir=True)

        parent.add_child(child)
        removed = parent.remove_child("child")

        assert removed == child
        assert "child" not in parent.children
        assert child.parent is None

    def test_remove_child_not_found(self) -> None:
        """Test removing a non-existent child."""
        parent = DirNode(path=Path("/parent"), name="parent", is_dir=True)

        removed = parent.remove_child("nonexistent")

        assert removed is None

    def test_remove_child_from_file_raises(self) -> None:
        """Test that removing a child from a file raises ValueError."""
        file_node = DirNode(path=Path("/file.txt"), name="file.txt", is_dir=False)

        with pytest.raises(ValueError):
            file_node.remove_child("child")

    def test_get_child(self) -> None:
        """Test getting a child by name."""
        parent = DirNode(path=Path("/parent"), name="parent", is_dir=True)
        child = DirNode(path=Path("/parent/child"), name="child", is_dir=True)

        parent.add_child(child)

        assert parent.get_child("child") == child
        assert parent.get_child("nonexistent") is None

    def test_set_size_file(self) -> None:
        """Test setting size on a file."""
        file_node = DirNode(path=Path("/file.txt"), name="file.txt", is_dir=False)
        file_node.set_size(1024)

        assert file_node.get_size() == 1024

    def test_set_size_propagates_to_parent(self) -> None:
        """Test that setting size propagates to parent."""
        parent = DirNode(path=Path("/parent"), name="parent", is_dir=True)
        child = DirNode(path=Path("/parent/child.txt"), name="child.txt", is_dir=False)

        parent.add_child(child)
        child.set_size(1024)

        assert child.get_size() == 1024
        assert parent.get_size() == 1024

    def test_set_size_multiple_updates(self) -> None:
        """Test multiple size updates propagate correctly."""
        parent = DirNode(path=Path("/parent"), name="parent", is_dir=True)
        child1 = DirNode(
            path=Path("/parent/child1.txt"), name="child1.txt", is_dir=False
        )
        child2 = DirNode(
            path=Path("/parent/child2.txt"), name="child2.txt", is_dir=False
        )

        parent.add_child(child1)
        parent.add_child(child2)

        child1.set_size(1000)
        child2.set_size(500)

        assert parent.get_size() == 1500

        child1.set_size(2000)

        assert parent.get_size() == 2500

    def test_mark_loaded(self) -> None:
        """Test marking a directory as loaded."""
        node = DirNode(path=Path("/dir"), name="dir", is_dir=True)

        assert node.is_loaded() is False

        node.mark_loaded()

        assert node.is_loaded() is True

    def test_get_item_count(self) -> None:
        """Test getting item count."""
        parent = DirNode(path=Path("/parent"), name="parent", is_dir=True)
        assert parent.get_item_count() == 0

        child1 = DirNode(path=Path("/parent/child1"), name="child1", is_dir=True)
        child2 = DirNode(path=Path("/parent/child2"), name="child2", is_dir=True)

        parent.add_child(child1)
        assert parent.get_item_count() == 1

        parent.add_child(child2)
        assert parent.get_item_count() == 2

    def test_file_get_item_count(self) -> None:
        """Test that files have zero item count."""
        file_node = DirNode(path=Path("/file.txt"), name="file.txt", is_dir=False)
        assert file_node.get_item_count() == 0

    def test_repr(self) -> None:
        """Test string representation."""
        dir_node = DirNode(path=Path("/dir"), name="dir", is_dir=True)
        file_node = DirNode(path=Path("/file.txt"), name="file.txt", is_dir=False)

        assert "dir" in repr(dir_node)
        assert "file" in repr(file_node)
        assert "dir" in repr(dir_node)
