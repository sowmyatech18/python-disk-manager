"""Tests for UI components."""

import tkinter as tk
from collections.abc import Generator
from pathlib import Path

import pytest

from ptdu.models import DirNode
from ptdu.treeview import DirectoryTreeview
from ptdu.ui import MainWindow


# Tests window creation, status-bar behavior, keyboard controls, and font sizing.
class TestMainWindow:
    """Tests for MainWindow class."""

    # Test that MainWindow creates a window with correct title.
    def test_window_creation(self) -> None:
        """Test that MainWindow creates a window with correct title."""
        # Arrange the test setup before checking the expected behavior.
        root = tk.Tk()
        try:
            window = MainWindow(root)
            assert window.root == root
            assert "PTDU" in window.root.title()
            window.cleanup()
        finally:
            root.destroy()

    # Test window geometry is set correctly.
    def test_window_geometry(self) -> None:
        """Test window geometry is set correctly."""
        # Arrange the test setup before checking the expected behavior.
        root = tk.Tk()
        try:
            window = MainWindow(root)
            # Check that geometry was set (format: WIDTHxHEIGHT+X+Y)
            geometry = root.geometry()
            assert "x" in geometry
            window.cleanup()
        finally:
            root.destroy()

    # Test that treeview is created.
    def test_treeview_exists(self) -> None:
        """Test that treeview is created."""
        # Arrange the test setup before checking the expected behavior.
        root = tk.Tk()
        try:
            window = MainWindow(root)
            assert isinstance(window.treeview, DirectoryTreeview)
            window.cleanup()
        finally:
            root.destroy()

    # Test that status bar widgets exist.
    def test_status_bar_widgets(self) -> None:
        """Test that status bar widgets exist."""
        # Arrange the test setup before checking the expected behavior.
        root = tk.Tk()
        try:
            window = MainWindow(root)
            assert hasattr(window, "path_var")
            assert hasattr(window, "items_var")
            assert hasattr(window, "status_var")
            assert hasattr(window, "path_label")
            assert hasattr(window, "items_label")
            assert hasattr(window, "status_label")
            window.cleanup()
        finally:
            root.destroy()

    # Test setting path in status bar.
    def test_set_path(self) -> None:
        """Test setting path in status bar."""
        # Arrange the test setup before checking the expected behavior.
        root = tk.Tk()
        try:
            window = MainWindow(root)
            window.set_path("/home/user")
            assert window.path_var.get() == "/home/user"
            window.cleanup()
        finally:
            root.destroy()

    # Test setting item count in status bar.
    def test_set_item_count(self) -> None:
        """Test setting item count in status bar."""
        # Arrange the test setup before checking the expected behavior.
        root = tk.Tk()
        try:
            window = MainWindow(root)
            window.set_item_count(42)
            assert window.items_var.get() == "Items: 42"
            window.cleanup()
        finally:
            root.destroy()

    # Test setting status message.
    def test_set_status(self) -> None:
        """Test setting status message."""
        # Arrange the test setup before checking the expected behavior.
        root = tk.Tk()
        try:
            window = MainWindow(root)
            window.set_status("Scanning...")
            assert window.status_var.get() == "Scanning..."
            window.cleanup()
        finally:
            root.destroy()

    # Test that keyboard bindings are set up.
    def test_keyboard_bindings_exist(self) -> None:
        """Test that keyboard bindings are set up."""
        # Arrange the test setup before checking the expected behavior.
        root = tk.Tk()
        try:
            window = MainWindow(root)
            # Check that bind methods were called (bindings exist)
            # The _bind_events method should have set up all bindings
            assert hasattr(window, "_on_down")
            assert hasattr(window, "_on_up")
            assert hasattr(window, "_on_expand")
            assert hasattr(window, "_on_collapse")
            assert hasattr(window, "_on_quit")
            assert hasattr(window, "_on_rescan")
            assert hasattr(window, "_on_jump_top")
            assert hasattr(window, "_on_jump_bottom")
            window.cleanup()
        finally:
            root.destroy()

    # Test that font size control methods exist.
    def test_font_size_controls_exist(self) -> None:
        """Test that font size control methods exist."""
        # Arrange the test setup before checking the expected behavior.
        root = tk.Tk()
        try:
            window = MainWindow(root)
            assert hasattr(window, "_on_increase_font")
            assert hasattr(window, "_on_decrease_font")
            assert hasattr(window, "_on_reset_font")
            assert hasattr(window, "_refresh_status_fonts")
            window.cleanup()
        finally:
            root.destroy()

    # Test font size increase and decrease functionality.
    def test_font_size_increase_decrease(self) -> None:
        """Test font size increase and decrease functionality."""
        # Arrange the test setup before checking the expected behavior.
        from ptdu.fonts import FontManager

        root = tk.Tk()
        try:
            font_manager = FontManager(root)
            initial_size = font_manager.get_font_size()

            # Test increase
            new_size = font_manager.increase_font_size()
            assert new_size == initial_size + 1 or new_size == font_manager.MAX_SIZE

            # Test decrease
            new_size = font_manager.decrease_font_size()
            assert new_size == initial_size

            # Test reset
            reset_size = font_manager.reset_font_size()
            assert reset_size == 13
        finally:
            root.destroy()

    # Test expand/collapse toggle.
    def test_toggle_expand_collapse(self) -> None:
        """Test expand/collapse toggle."""
        # Arrange the test setup before checking the expected behavior.
        import tkinter as tk

        root = tk.Tk()
        try:
            from ptdu.models import DirNode
            from ptdu.treeview import DirectoryTreeview

            tree = DirectoryTreeview(root)
            node = DirNode(path=Path("/testdir"), name="testdir", is_dir=True)

            iid = tree.insert_node("", node)

            # Initially collapsed
            assert tree.item(iid, "open") == 0

            # Expand
            tree.expand_node(iid)
            assert tree.item(iid, "open") == 1
            assert node.is_expanded is True

            # Collapse
            tree.collapse_node(iid)
            assert tree.item(iid, "open") == 0
            assert node.is_expanded is False
        finally:
            root.destroy()


# Tests directory-tree columns, node operations, selection, and file styling.
class TestDirectoryTreeview:
    """Tests for DirectoryTreeview class."""

    @pytest.fixture
    def treeview(self) -> Generator[DirectoryTreeview, None, None]:
        """Create a treeview for testing."""
        import tkinter as tk

        root = tk.Tk()
        tree = DirectoryTreeview(root)  # type: ignore[arg-type]
        yield tree
        root.destroy()

    # Test treeview is created with correct columns.
    def test_treeview_creation(self, treeview: DirectoryTreeview) -> None:
        """Test treeview is created with correct columns."""
        assert treeview.COL_NAME == "name"
        assert treeview.COL_SIZE == "size"
        assert treeview.COL_PERCENT == "percent"
        assert treeview.COL_ITEMS == "items"

    # Test that columns are configured.
    def test_columns_configured(self, treeview: DirectoryTreeview) -> None:
        """Test that columns are configured."""
        # Arrange the test setup before checking the expected behavior.
        columns = treeview["columns"]
        assert treeview.COL_SIZE in columns
        assert treeview.COL_PERCENT in columns
        assert treeview.COL_ITEMS in columns

    # Test that styling tags are configured.
    def test_tags_configured(self, treeview: DirectoryTreeview) -> None:
        """Test that styling tags are configured."""
        # Tags are configured during initialization
        # Just verify no errors occur
        assert DirectoryTreeview.TAG_DIRECTORY == "directory"
        assert DirectoryTreeview.TAG_FILE == "file"
        assert DirectoryTreeview.TAG_HIDDEN == "hidden"
        assert DirectoryTreeview.TAG_LARGE_FILE == "large_file"
        assert DirectoryTreeview.TAG_MEDIUM_FILE == "medium_file"

    # Test inserting a file node.
    def test_insert_file_node(self) -> None:
        """Test inserting a file node."""
        # Arrange the test setup before checking the expected behavior.
        import tkinter as tk

        root = tk.Tk()
        try:
            tree = DirectoryTreeview(root)  # type: ignore[arg-type]
            node = DirNode(path=Path("/test.txt"), name="test.txt", is_dir=False)
            node.size = 1024

            iid = tree.insert_node("", node)

            assert iid == str(node.path)
            assert iid in tree.get_children()
            assert tree.get_node(iid) == node
        finally:
            root.destroy()

    # Test inserting a directory node.
    def test_insert_directory_node(self) -> None:
        """Test inserting a directory node."""
        # Arrange the test setup before checking the expected behavior.
        import tkinter as tk

        root = tk.Tk()
        try:
            tree = DirectoryTreeview(root)  # type: ignore[arg-type]
            node = DirNode(path=Path("/testdir"), name="testdir", is_dir=True)
            node.size = 0

            iid = tree.insert_node("", node)

            assert iid == str(node.path)
            assert iid in tree.get_children()
        finally:
            root.destroy()

    # Test that get_node returns None for invalid iid.
    def test_get_node_returns_none_for_invalid(
        self, treeview: DirectoryTreeview
    ) -> None:
        """Test that get_node returns None for invalid iid."""
        assert treeview.get_node("invalid") is None

    # Test that clear removes all items.
    def test_clear_removes_all(self) -> None:
        """Test that clear removes all items."""
        # Arrange the test setup before checking the expected behavior.
        import tkinter as tk

        root = tk.Tk()
        try:
            tree = DirectoryTreeview(root)  # type: ignore[arg-type]
            node1 = DirNode(path=Path("/test1.txt"), name="test1.txt", is_dir=False)
            node2 = DirNode(path=Path("/test2.txt"), name="test2.txt", is_dir=False)

            tree.insert_node("", node1)
            tree.insert_node("", node2)

            assert len(tree.get_children()) == 2

            tree.clear()

            assert len(tree.get_children()) == 0
            assert tree.get_node(str(node1.path)) is None
        finally:
            root.destroy()

    # Test that hidden files get hidden tag.
    def test_hidden_file_tag(self) -> None:
        """Test that hidden files get hidden tag."""
        # Arrange the test setup before checking the expected behavior.
        import tkinter as tk

        root = tk.Tk()
        try:
            tree = DirectoryTreeview(root)  # type: ignore[arg-type]
            hidden_node = DirNode(path=Path("/.hidden"), name=".hidden", is_dir=False)
            visible_node = DirNode(path=Path("/visible"), name="visible", is_dir=False)

            tree.insert_node("", hidden_node)
            tree.insert_node("", visible_node)

            tags = tree.item(str(hidden_node.path), "tags")
            assert DirectoryTreeview.TAG_HIDDEN in tags

            tags = tree.item(str(visible_node.path), "tags")
            assert DirectoryTreeview.TAG_HIDDEN not in tags
        finally:
            root.destroy()

    # Test that large files get large_file tag.
    def test_large_file_tag(self) -> None:
        """Test that large files get large_file tag."""
        # Arrange the test setup before checking the expected behavior.
        import tkinter as tk

        root = tk.Tk()
        try:
            tree = DirectoryTreeview(root)  # type: ignore[arg-type]
            large_node = DirNode(
                path=Path("/large.bin"), name="large.bin", is_dir=False
            )
            large_node.size = 200 * 1024 * 1024  # 200MB

            tree.insert_node("", large_node)

            tags = tree.item(str(large_node.path), "tags")
            assert DirectoryTreeview.TAG_LARGE_FILE in tags
        finally:
            root.destroy()

    # Test that setting max size updates percentage display.
    def test_set_max_size_updates_percent(self) -> None:
        """Test that setting max size updates percentage display."""
        # Arrange the test setup before checking the expected behavior.
        import tkinter as tk

        root = tk.Tk()
        try:
            tree = DirectoryTreeview(root)  # type: ignore[arg-type]
            node = DirNode(path=Path("/test.txt"), name="test.txt", is_dir=False)
            node.size = 50

            tree.set_max_size(100)
            iid = tree.insert_node("", node)

            values = tree.item(iid, "values")
            # values format: (size, size_bar, percent, items)
            assert "50%" in values[2]
        finally:
            root.destroy()

    # Test expand and collapse operations.
    def test_expand_collapse_node(self) -> None:
        """Test expand and collapse operations."""
        # Arrange the test setup before checking the expected behavior.
        import tkinter as tk

        root = tk.Tk()
        try:
            tree = DirectoryTreeview(root)  # type: ignore[arg-type]
            node = DirNode(path=Path("/testdir"), name="testdir", is_dir=True)

            iid = tree.insert_node("", node)

            # Expand
            tree.expand_node(iid)
            assert node.is_expanded is True
            assert tree.item(iid, "open") == 1

            # Collapse
            tree.collapse_node(iid)
            assert node.is_expanded is False
            assert tree.item(iid, "open") == 0
        finally:
            root.destroy()

    # Test selecting a node.
    def test_select_node(self) -> None:
        """Test selecting a node."""
        # Arrange the test setup before checking the expected behavior.
        import tkinter as tk

        root = tk.Tk()
        try:
            tree = DirectoryTreeview(root)  # type: ignore[arg-type]
            node = DirNode(path=Path("/test.txt"), name="test.txt", is_dir=False)

            iid = tree.insert_node("", node)
            tree.select_node(iid)

            selection = tree.selection()
            assert iid in selection
        finally:
            root.destroy()

    # Test getting selected node.
    def test_get_selected_node(self) -> None:
        """Test getting selected node."""
        # Arrange the test setup before checking the expected behavior.
        import tkinter as tk

        root = tk.Tk()
        try:
            tree = DirectoryTreeview(root)  # type: ignore[arg-type]
            node = DirNode(path=Path("/test.txt"), name="test.txt", is_dir=False)

            iid = tree.insert_node("", node)
            tree.select_node(iid)

            selected = tree.get_selected_node()
            assert selected == node
        finally:
            root.destroy()

    # Test that get_selected_node returns None when nothing selected.
    def test_get_selected_node_none(self) -> None:
        """Test that get_selected_node returns None when nothing selected."""
        # Arrange the test setup before checking the expected behavior.
        import tkinter as tk

        root = tk.Tk()
        try:
            tree = DirectoryTreeview(root)  # type: ignore[arg-type]
            assert tree.get_selected_node() is None
        finally:
            root.destroy()
