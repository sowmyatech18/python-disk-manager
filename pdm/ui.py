"""UI components for PTDU."""

from __future__ import annotations

import csv
import json
import tkinter as tk
from enum import Enum, auto
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional, TypedDict


# Class responsibility: Type for export data items.
class ExportDataItem(TypedDict):
    """Type for export data items."""

    path: str
    name: str
    size: int
    size_human: int
    is_dir: bool
    item_count: int

from ptdu.cache import ScanCache
from ptdu.errors import ErrorHandler, PathValidator, get_error_handler
from ptdu.fonts import FontManager
from ptdu.models import DirNode
from ptdu.performance import LargeDirectoryHandler, VirtualScroller
from ptdu.scanner import Scanner
from ptdu.threads import (
    ScanComplete,
    ScanError,
    ScanMessage,
    ScanProgress,
    ScanThreadManager,
)
from ptdu.treeview import DirectoryTreeview


# Class responsibility: Sorting modes for directory contents.
class SortMode(Enum):
    """Sorting modes for directory contents."""

    SIZE = auto()
    NAME = auto()
    COUNT = auto()


# Class responsibility: Main application window for PTDU.
class MainWindow:
    """Main application window for PTDU."""

    DEFAULT_WIDTH: int = 900
    DEFAULT_HEIGHT: int = 600
    MESSAGE_CHECK_INTERVAL: int = 50  # milliseconds

    # Sort mode display names
    SORT_MODE_NAMES: dict[SortMode, str] = {
        SortMode.SIZE: "Size",
        SortMode.NAME: "Name",
        SortMode.COUNT: "Items",
    }

    # Method/function purpose: Initialize the main window.
    def __init__(self, root: Optional[tk.Tk] = None) -> None:
        """Initialize the main window.

        Args:
            root: Optional Tk root window. Creates one if not provided.
        """
        self.root: tk.Tk = root if root is not None else tk.Tk()
        self._setup_window()

        # Font manager for OS-aware fonts (must be before _create_layout)
        self._font_manager: FontManager = FontManager(self.root)

        self._create_layout()

        # Thread manager for background scanning
        self._scan_manager: ScanThreadManager = ScanThreadManager()
        self._scanner: Optional[Scanner] = None
        self._after_id: Optional[str] = None
        self._root_path: Path = Path(".")

        # Breadcrumb UI components (initialized on demand)
        self._breadcrumb_container: ttk.Frame | None = None

        # Sorting mode
        self._sort_mode: SortMode = SortMode.SIZE

        # Filter state
        self._show_hidden: bool = True

        # Error handler
        self._error_handler: ErrorHandler = get_error_handler()
        self._error_handler.set_parent(self.root)

        # Performance optimizations
        self._virtual_scroller: VirtualScroller = VirtualScroller()
        self._large_dir_handler: LargeDirectoryHandler = LargeDirectoryHandler()
        self._max_depth: Optional[int] = None

        # Cache reference
        self._cache: Optional[ScanCache] = None

        # Start checking for messages
        self._schedule_message_check()

        # Bind events
        self._bind_events()

    # Method/function purpose: Bind keyboard and mouse events.
    def _bind_events(self) -> None:
        """Bind keyboard and mouse events."""
        # Treeview selection and expansion events
        self.treeview.bind("<Double-1>", self._on_double_click)
        self.treeview.bind("<Return>", self._on_enter_key)

        # Keyboard navigation (vim-style)
        self.root.bind("j", self._on_down)
        self.root.bind("k", self._on_up)
        self.root.bind("<Down>", self._on_down)
        self.root.bind("<Up>", self._on_up)

        # Expand/collapse
        self.root.bind("h", self._on_collapse)
        self.root.bind("l", self._on_expand)
        self.root.bind("<Left>", self._on_collapse)
        self.root.bind("<Right>", self._on_expand)

        # Jump to top/bottom
        self.root.bind("g", self._on_jump_top)
        self.root.bind("G", self._on_jump_bottom)

        # Action keys
        self.root.bind("q", self._on_quit)
        self.root.bind("r", self._on_rescan)
        self.root.bind("d", self._on_delete)
        self.root.bind("b", self._on_toggle_breadcrumb)
        self.root.bind("u", self._on_parent_directory)

        # Font size controls (Ctrl+Plus/Ctrl+Minus)
        self.root.bind("<Control-plus>", self._on_increase_font)
        self.root.bind(
            "<Control-equal>", self._on_increase_font
        )  # For keyboards without numpad
        self.root.bind("<Control-minus>", self._on_decrease_font)
        self.root.bind("<Control-0>", self._on_reset_font)

        # Sorting (s key to cycle)
        self.root.bind("s", self._on_cycle_sort)

        # Toggle hidden files (. key)
        self.root.bind(".", self._on_toggle_hidden)

        # Export (e key)
        self.root.bind("e", self._on_export)

        # Open folder (Ctrl+O)
        self.root.bind("<Control-o>", self._on_open_folder_event)

        # Breadcrumb frame (initially hidden)
        self._breadcrumb_visible: bool = False
        self._breadcrumb_frame: ttk.Frame | None = None
        self._breadcrumb_labels: list[ttk.Label] = []

    # Method/function purpose: Handle double-click on treeview item.
    def _on_double_click(self, event: tk.Event) -> str | None:
        """Handle double-click on treeview item."""
        # Identify which tree row was clicked using the mouse's vertical position.
        item = self.treeview.identify_row(event.y)
        if item:
            self._toggle_expand_collapse(item)
        return None

    # Method/function purpose: Handle Enter key press.
    def _on_enter_key(self, event: tk.Event) -> str | None:
        """Handle Enter key press."""
        # Read the currently selected tree item.
        selection = self.treeview.selection()
        if selection:
            self._toggle_expand_collapse(selection[0])
        return None

    # Method/function purpose: Toggle expand/collapse state of an item.
    def _toggle_expand_collapse(self, item: str) -> None:
        """Toggle expand/collapse state of an item."""
        # Retrieve the directory-tree model associated with this UI item.
        node = self.treeview.get_node(item)
        if node is None or not node.is_dir:
            return

        if self.treeview.item(item, "open"):
            self.treeview.collapse_node(item)
        else:
            self.treeview.expand_node(item)

    # Method/function purpose: Move selection down.
    def _on_down(self, event: tk.Event) -> str | None:
        """Move selection down."""
        selection = self.treeview.selection()
        if not selection:
            # Select first item
            children = self.treeview.get_children()
            if children:
                self.treeview.select_node(children[0])
        else:
            # Get next sibling or parent's next sibling
            current = selection[0]
            # Find the next sibling row in the tree.
            next_item = self.treeview.next(current)
            if next_item:
                self.treeview.select_node(next_item)
            else:
                # Try to find next of parent
                parent = self.treeview.parent(current)
                if parent:
                    next_of_parent = self.treeview.next(parent)
                    if next_of_parent:
                        self.treeview.select_node(next_of_parent)
        return "break"

    # Method/function purpose: Move selection up.
    def _on_up(self, event: tk.Event) -> str | None:
        """Move selection up."""
        selection = self.treeview.selection()
        if not selection:
            return "break"

        current = selection[0]
        # Find the previous sibling row in the tree.
        prev_item = self.treeview.prev(current)
        if prev_item:
            self.treeview.select_node(prev_item)
        else:
            # Select parent
            parent = self.treeview.parent(current)
            if parent:
                self.treeview.select_node(parent)
        return "break"

    # Method/function purpose: Expand selected directory.
    def _on_expand(self, event: tk.Event) -> str | None:
        """Expand selected directory."""
        selection = self.treeview.selection()
        if selection:
            self.treeview.expand_node(selection[0])
        return "break"

    # Method/function purpose: Collapse selected directory.
    def _on_collapse(self, event: tk.Event) -> str | None:
        """Collapse selected directory."""
        selection = self.treeview.selection()
        if selection:
            self.treeview.collapse_node(selection[0])
        return "break"

    # Method/function purpose: Jump to first item.
    def _on_jump_top(self, event: tk.Event) -> str | None:
        """Jump to first item."""
        children = self.treeview.get_children()
        if children:
            self.treeview.select_node(children[0])
        return "break"

    # Method/function purpose: Jump to last visible item.
    def _on_jump_bottom(self, event: tk.Event) -> str | None:
        """Jump to last visible item."""

        # Get all visible items
        # Walk down expanded children to locate the last visible row.
        def get_last_visible(item: str) -> str:
            if self.treeview.item(item, "open"):
                children = self.treeview.get_children(item)
                if children:
                    return get_last_visible(children[-1])
            return item

        children = self.treeview.get_children()
        if children:
            last = get_last_visible(children[-1])
            self.treeview.select_node(last)
        return "break"

    # Method/function purpose: Quit application.
    def _on_quit(self, event: tk.Event) -> str | None:
        """Quit application."""
        self.quit()
        return "break"

    # Method/function purpose: Rescan current directory.
    def _on_rescan(self, event: tk.Event) -> str | None:
        """Rescan current directory."""
        selection = self.treeview.selection()
        if selection:
            node = self.treeview.get_node(selection[0])
            if node is not None and node.is_dir:
                self.treeview.delete(*self.treeview.get_children(selection[0]))
                node.children.clear()
                self.start_background_scan(node.path, node, selection[0])
        else:
            # Rescan root
            self.treeview.clear()
            if self._scanner is not None:
                self.start_background_scan(self._root_path)
        return "break"

    # Method/function purpose: Delete selected item with confirmation.
    def _on_delete(self, event: tk.Event) -> str | None:
        """Delete selected item with confirmation."""
        selection = self.treeview.selection()
        if not selection:
            return "break"

        node = self.treeview.get_node(selection[0])
        if node is None:
            return "break"

        # Show confirmation dialog
        item_type = "directory" if node.is_dir else "file"
        # Ask for explicit confirmation before deleting anything from disk.
        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete this {item_type}?\n\n{node.path}",
            icon="warning",
        )

        if not confirm:
            return "break"

        try:
            # Try to use send2trash first (safer - moves to trash)
            try:
                # Import the safer recycle-bin option only when it is available.
                from send2trash import send2trash

                send2trash(str(node.path))
                method = "moved to trash"
            except ImportError:
                # Fallback to permanent deletion
                import shutil

                if node.is_dir:
                    shutil.rmtree(node.path)
                else:
                    node.path.unlink()
                method = "deleted permanently"

            # Remove from treeview
            self.treeview.delete_node(selection[0])

            # Update status
            self.set_status(f"Deleted: {node.name} ({method})")

        except Exception as e:
            messagebox.showerror(
                "Delete Failed",
                f"Failed to delete {node.name}:\n{str(e)}",
            )

        return "break"

    # Method/function purpose: Toggle breadcrumb path bar visibility.
    def _on_toggle_breadcrumb(self, event: tk.Event) -> str | None:
        """Toggle breadcrumb path bar visibility."""
        if self._breadcrumb_frame is None:
            self._create_breadcrumb()

        if self._breadcrumb_frame is not None:
            if self._breadcrumb_visible:
                self._breadcrumb_frame.grid_remove()
                self._breadcrumb_visible = False
            else:
                self._breadcrumb_frame.grid()
                self._update_breadcrumb()
                self._breadcrumb_visible = True

        return "break"

    # Method/function purpose: Create the breadcrumb path bar.
    def _create_breadcrumb(self) -> None:
        """Create the breadcrumb path bar."""
        self._breadcrumb_frame = ttk.Frame(
            self.main_frame, relief="groove", padding="2"
        )
        self._breadcrumb_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        self._breadcrumb_frame.grid_remove()  # Initially hidden

        # Container for path segments
        self._breadcrumb_container = ttk.Frame(self._breadcrumb_frame)
        self._breadcrumb_container.pack(fill="x", expand=True)

    # Method/function purpose: Update breadcrumb display with current path.
    def _update_breadcrumb(self) -> None:
        """Update breadcrumb display with current path."""
        if self._breadcrumb_frame is None:
            return

        # Clear existing labels
        for label in self._breadcrumb_labels:
            label.destroy()
        self._breadcrumb_labels.clear()

        # Get current path from selection or root
        selection = self.treeview.selection()
        if selection:
            node = self.treeview.get_node(selection[0])
            current_path = node.path if node else self._root_path
        else:
            current_path = getattr(self, "_root_path", Path("."))

        # Create path segments
        # Build the path components in root-to-leaf order.
        parts: list[Path] = []
        current = current_path
        while current != current.parent:
            parts.insert(0, current)
            current = current.parent
        parts.insert(0, current)  # Add root

        # Create labels for each segment
        for i, part in enumerate(parts):
            # Separator
            if i > 0:
                sep = ttk.Label(self._breadcrumb_container, text=" > ")
                sep.pack(side="left")
                self._breadcrumb_labels.append(sep)

            # Clickable path segment
            label = ttk.Label(
                self._breadcrumb_container,
                text=part.name if part.name else str(part),
                foreground="blue",
                cursor="hand2",
            )
            label.pack(side="left")
            label.bind(
                "<Button-1>",
                lambda e, p=part: self._navigate_to_path(p),  # type: ignore[misc]
            )
            self._breadcrumb_labels.append(label)

    # Method/function purpose: Navigate to a specific path.
    def _navigate_to_path(self, path: Path) -> None:
        """Navigate to a specific path."""
        # Find the item in treeview
        # Convert the filesystem path to the treeview's item identifier.
        iid = str(path)
        node = self.treeview.get_node(iid)

        if node is not None:
            # Select and show the node
            self.treeview.select_node(iid)
            # Expand all parents
            current = iid
            while True:
                parent = self.treeview.parent(current)
                if not parent:
                    break
                self.treeview.expand_node(parent)
                current = parent

    # Method/function purpose: Navigate to parent directory.
    def _on_parent_directory(self, event: tk.Event) -> str | None:
        """Navigate to parent directory."""
        selection = self.treeview.selection()
        if not selection:
            # If nothing selected, select first item
            children = self.treeview.get_children()
            if children:
                self.treeview.select_node(children[0])
            return "break"

        current = selection[0]
        parent = self.treeview.parent(current)

        if parent:
            self.treeview.select_node(parent)
        else:
            # Already at root, try to find parent in filesystem
            node = self.treeview.get_node(current)
            if node and node.path != node.path.parent:
                # Create parent node if needed
                parent_path = node.path.parent
                parent_iid = str(parent_path)

                # Check if parent already exists
                if self.treeview.get_node(parent_iid) is None:
                    parent_node = DirNode(
                        path=parent_path,
                        name=parent_path.name if parent_path.name else str(parent_path),
                        is_dir=True,
                    )
                    parent_node.is_expanded = True
                    # Insert at top level (we'll need to reorganize tree)
                    self.treeview.insert_node("", parent_node)

                self.treeview.select_node(parent_iid)

        return "break"

    # Method/function purpose: Cycle through sorting modes.
    def _on_cycle_sort(self, event: tk.Event) -> str | None:
        """Cycle through sorting modes."""
        # Get next sort mode
        # Create an ordered list of the available sorting modes.
        modes = list(SortMode)
        current_index = modes.index(self._sort_mode)
        next_index = (current_index + 1) % len(modes)
        self._sort_mode = modes[next_index]

        # Show status
        self.set_status(f"Sort: {self.SORT_MODE_NAMES[self._sort_mode]}")

        # Re-sort the current view if we have items
        self._resort_treeview()

        return "break"

    # Method/function purpose: Toggle visibility of hidden files (dotfiles).
    def _on_toggle_hidden(self, event: tk.Event) -> str | None:
        """Toggle visibility of hidden files (dotfiles)."""
        self._show_hidden = not self._show_hidden

        status = "shown" if self._show_hidden else "hidden"
        self.set_status(f"Hidden files: {status}")

        # Trigger a rescan to apply the filter
        self._on_rescan(event)

        return "break"

    # Method/function purpose: Event handler for open folder.
    def _on_open_folder_event(self, event: tk.Event) -> str | None:
        """Event handler for open folder."""
        self._on_open_folder()
        return "break"

    # Method/function purpose: Export current scan results to JSON or CSV.
    def _on_export(self, event: tk.Event) -> str | None:
        """Export current scan results to JSON or CSV."""
        # Ask user for export format
        formats = [
            ("JSON files", "*.json"),
            ("CSV files", "*.csv"),
            ("All files", "*.*"),
        ]
        # Open a Save As dialog so the user can choose the export destination.
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=formats,
            title="Export Scan Results",
        )

        if not filename:
            return "break"

        try:
            filepath = Path(filename)
            if filepath.suffix.lower() == ".json":
                self._export_json(filepath)
            elif filepath.suffix.lower() == ".csv":
                self._export_csv(filepath)
            else:
                # Default to JSON
                self._export_json(filepath.with_suffix(".json"))

            self.set_status(f"Exported to {filepath.name}")

        except Exception as e:
            messagebox.showerror(
                "Export Failed",
                f"Failed to export results:\n{str(e)}",
            )

        return "break"

    # Method/function purpose: Collect current treeview data for export.
    def _collect_export_data(self) -> list[ExportDataItem]:
        """Collect current treeview data for export."""
        data: list[ExportDataItem] = []

        # Visit each tree item and collect the fields needed for export.
        def collect_items(parent_iid: str = "") -> None:
            for iid in self.treeview.get_children(parent_iid):
                node = self.treeview.get_node(iid)
                if node is not None:
                    data.append(
                        {
                            "path": str(node.path),
                            "name": node.name,
                            "size": node.size,
                            "size_human": self.treeview._font_manager.measure_text_width(
                                node.name, "treeview"
                            ),
                            "is_dir": node.is_dir,
                            "item_count": node.get_item_count() if node.is_dir else 0,
                        }
                    )
                    # Recursively collect children
                    if node.is_dir:
                        collect_items(iid)

        collect_items()
        return data

    # Method/function purpose: Export data to JSON format.
    def _export_json(self, filepath: Path) -> None:
        """Export data to JSON format."""
        data = self._collect_export_data()

        # Add metadata
        export_data = {
            "exported_from": str(self._root_path),
            "total_items": len(data),
            "items": data,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            # Write readable JSON while preserving non-ASCII characters.
            json.dump(export_data, f, indent=2, ensure_ascii=False)

    # Method/function purpose: Export data to CSV format.
    def _export_csv(self, filepath: Path) -> None:
        """Export data to CSV format."""
        data = self._collect_export_data()

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            # Create a CSV writer with the selected column names.
            writer = csv.DictWriter(
                f,
                fieldnames=["path", "name", "size", "is_dir", "item_count"],
            )
            writer.writeheader()
            writer.writerows(data)

    # Method/function purpose: Get sort key for a node based on current sort mode.
    def _get_sort_key(self, node: DirNode) -> tuple[object, ...]:
        """Get sort key for a node based on current sort mode.

        Returns:
            Tuple for sorting (directories first, then by sort criteria)
        """
        # Always put directories first, then sort by criteria
        if self._sort_mode == SortMode.SIZE:
            # Sort by size descending, then by name ascending
            # Directories sort first; within each group, larger sizes come first.
            return (0 if node.is_dir else 1, -node.size, node.name.lower())
        elif self._sort_mode == SortMode.NAME:
            # Sort by name ascending
            # Directories sort first, followed by names in case-insensitive order.
            return (0 if node.is_dir else 1, node.name.lower())
        else:  # SortMode.COUNT
            # Sort by item count descending, then by name
            count = node.get_item_count() if node.is_dir else 0
            return (0 if node.is_dir else 1, -count, node.name.lower())

    # Method/function purpose: Re-sort all items in the treeview.
    def _resort_treeview(self) -> None:
        """Re-sort all items in the treeview."""
        # Get all items and their nodes
        items_to_move: list[tuple[str, str, DirNode]] = []  # (parent_iid, iid, node)

        def collect_items(parent_iid: str = "") -> None:
            for iid in self.treeview.get_children(parent_iid):
                node = self.treeview.get_node(iid)
                if node is not None:
                    items_to_move.append((parent_iid, iid, node))
                    # Recursively collect children
                    if node.is_dir:
                        collect_items(iid)

        collect_items()

        # Sort by current sort mode
        items_to_move.sort(key=lambda x: self._get_sort_key(x[2]))

        # Move items to their new positions within each parent
        # Group by parent
        # Import groupby to process tree items grouped by their parent.
        from itertools import groupby

        items_to_move.sort(key=lambda x: x[0])  # Sort by parent first
        for parent_iid, group in groupby(items_to_move, key=lambda x: x[0]):
            group_list = list(group)
            # Sort this parent's children
            group_list.sort(key=lambda x: self._get_sort_key(x[2]))
            # Move each item to the end in sorted order
            for _, iid, _ in group_list:
                self.treeview.move(iid, parent_iid, "end")

    # Method/function purpose: Increase font size.
    def _on_increase_font(self, event: tk.Event) -> str | None:
        """Increase font size."""
        new_size = self._font_manager.increase_font_size()
        self.treeview.refresh_fonts()
        self._refresh_status_fonts()
        self.set_status(f"Font size: {new_size}pt")
        return "break"

    # Method/function purpose: Decrease font size.
    def _on_decrease_font(self, event: tk.Event) -> str | None:
        """Decrease font size."""
        new_size = self._font_manager.decrease_font_size()
        self.treeview.refresh_fonts()
        self._refresh_status_fonts()
        self.set_status(f"Font size: {new_size}pt")
        return "break"

    # Method/function purpose: Reset font size to default.
    def _on_reset_font(self, event: tk.Event) -> str | None:
        """Reset font size to default."""
        new_size = self._font_manager.reset_font_size()
        self.treeview.refresh_fonts()
        self._refresh_status_fonts()
        self.set_status(f"Font size: {new_size}pt (default)")
        return "break"

    # Method/function purpose: Refresh status bar fonts after size change.
    def _refresh_status_fonts(self) -> None:
        """Refresh status bar fonts after size change."""
        status_font = self._font_manager.get_status_font()
        self.path_label.configure(font=status_font)
        self.items_label.configure(font=status_font)
        self.status_label.configure(font=status_font)

    # Method/function purpose: Configure the main window properties.
    def _setup_window(self) -> None:
        """Configure the main window properties."""
        self.root.title("PTDU - Python Tkinter Disk Usage")
        self.root.geometry(self._get_centered_geometry())
        self.root.minsize(600, 400)

        # Set up grid weights for resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

    # Method/function purpose: Calculate centered window geometry string.
    def _get_centered_geometry(self) -> str:
        """Calculate centered window geometry string.

        Returns:
            Geometry string in format 'WIDTHxHEIGHT+X+Y'
        """
        # Read the screen dimensions to calculate a centered window position.
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        x = (screen_width - self.DEFAULT_WIDTH) // 2
        y = (screen_height - self.DEFAULT_HEIGHT) // 2

        return f"{self.DEFAULT_WIDTH}x{self.DEFAULT_HEIGHT}+{x}+{y}"

    # Method/function purpose: Create the application menubar with keyboard shortcuts.
    def _create_menubar(self) -> None:
        """Create the application menubar with keyboard shortcuts."""
        # Create the application's top-level menu bar.
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(
            label="Open Folder...",
            command=self._on_open_folder,
            accelerator="Ctrl+O",
        )
        file_menu.add_separator()
        file_menu.add_command(
            label="Export...",
            command=self._on_export_menu,
            accelerator="E",
        )
        file_menu.add_separator()
        file_menu.add_command(
            label="Quit",
            command=self.quit,
            accelerator="Q",
        )

        # View Menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(
            label="Toggle Hidden Files",
            command=self._on_toggle_hidden_menu,
            accelerator=".",
        )
        view_menu.add_command(
            label="Toggle Breadcrumb",
            command=self._on_toggle_breadcrumb_menu,
            accelerator="B",
        )
        view_menu.add_separator()
        view_menu.add_command(
            label="Increase Font Size",
            command=self._on_increase_font_menu,
            accelerator="Ctrl++",
        )
        view_menu.add_command(
            label="Decrease Font Size",
            command=self._on_decrease_font_menu,
            accelerator="Ctrl+-",
        )
        view_menu.add_command(
            label="Reset Font Size",
            command=self._on_reset_font_menu,
            accelerator="Ctrl+0",
        )

        # Sort Menu
        sort_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Sort", menu=sort_menu)
        sort_menu.add_command(
            label="Cycle Sort Mode",
            command=self._on_cycle_sort_menu,
            accelerator="S",
        )

        # Navigation Menu
        nav_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Navigation", menu=nav_menu)
        nav_menu.add_command(
            label="Up",
            command=self._on_up_menu,
            accelerator="K or ↑",
        )
        nav_menu.add_command(
            label="Down",
            command=self._on_down_menu,
            accelerator="J or ↓",
        )
        nav_menu.add_separator()
        nav_menu.add_command(
            label="Expand",
            command=self._on_expand_menu,
            accelerator="L or →",
        )
        nav_menu.add_command(
            label="Collapse",
            command=self._on_collapse_menu,
            accelerator="H or ←",
        )
        nav_menu.add_separator()
        nav_menu.add_command(
            label="Jump to Top",
            command=self._on_jump_top_menu,
            accelerator="G",
        )
        nav_menu.add_command(
            label="Jump to Bottom",
            command=self._on_jump_bottom_menu,
            accelerator="Shift+G",
        )
        nav_menu.add_separator()
        nav_menu.add_command(
            label="Go to Parent",
            command=self._on_parent_directory_menu,
            accelerator="U",
        )

        # Actions Menu
        actions_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Actions", menu=actions_menu)
        actions_menu.add_command(
            label="Rescan",
            command=self._on_rescan_menu,
            accelerator="R",
        )
        actions_menu.add_command(
            label="Delete Selected",
            command=self._on_delete_menu,
            accelerator="D",
        )

    # Method/function purpose: Open a different folder.
    def _on_open_folder(self) -> None:
        """Open a different folder."""
        folder = filedialog.askdirectory(title="Select Folder to Analyze")
        if folder:
            path = Path(folder)
            if path.exists() and path.is_dir():
                self._root_path = path
                self.treeview.clear()
                self.start_background_scan(path)

    # Method/function purpose: Menu callback for export.
    def _on_export_menu(self) -> None:
        """Menu callback for export."""
        self._on_export(tk.Event())

    # Method/function purpose: Menu callback for toggle hidden.
    def _on_toggle_hidden_menu(self) -> None:
        """Menu callback for toggle hidden."""
        self._on_toggle_hidden(tk.Event())

    # Method/function purpose: Menu callback for toggle breadcrumb.
    def _on_toggle_breadcrumb_menu(self) -> None:
        """Menu callback for toggle breadcrumb."""
        self._on_toggle_breadcrumb(tk.Event())

    # Method/function purpose: Menu callback for increase font.
    def _on_increase_font_menu(self) -> None:
        """Menu callback for increase font."""
        self._on_increase_font(tk.Event())

    # Method/function purpose: Menu callback for decrease font.
    def _on_decrease_font_menu(self) -> None:
        """Menu callback for decrease font."""
        self._on_decrease_font(tk.Event())

    # Method/function purpose: Menu callback for reset font.
    def _on_reset_font_menu(self) -> None:
        """Menu callback for reset font."""
        self._on_reset_font(tk.Event())

    # Method/function purpose: Menu callback for cycle sort.
    def _on_cycle_sort_menu(self) -> None:
        """Menu callback for cycle sort."""
        self._on_cycle_sort(tk.Event())

    # Method/function purpose: Menu callback for up navigation.
    def _on_up_menu(self) -> None:
        """Menu callback for up navigation."""
        self._on_up(tk.Event())

    # Method/function purpose: Menu callback for down navigation.
    def _on_down_menu(self) -> None:
        """Menu callback for down navigation."""
        self._on_down(tk.Event())

    # Method/function purpose: Menu callback for expand.
    def _on_expand_menu(self) -> None:
        """Menu callback for expand."""
        self._on_expand(tk.Event())

    # Method/function purpose: Menu callback for collapse.
    def _on_collapse_menu(self) -> None:
        """Menu callback for collapse."""
        self._on_collapse(tk.Event())

    # Method/function purpose: Menu callback for jump top.
    def _on_jump_top_menu(self) -> None:
        """Menu callback for jump top."""
        self._on_jump_top(tk.Event())

    # Method/function purpose: Menu callback for jump bottom.
    def _on_jump_bottom_menu(self) -> None:
        """Menu callback for jump bottom."""
        self._on_jump_bottom(tk.Event())

    # Method/function purpose: Menu callback for parent directory.
    def _on_parent_directory_menu(self) -> None:
        """Menu callback for parent directory."""
        self._on_parent_directory(tk.Event())

    # Method/function purpose: Menu callback for rescan.
    def _on_rescan_menu(self) -> None:
        """Menu callback for rescan."""
        self._on_rescan(tk.Event())

    # Method/function purpose: Menu callback for delete.
    def _on_delete_menu(self) -> None:
        """Menu callback for delete."""
        self._on_delete(tk.Event())

    # Method/function purpose: Create the main window layout.
    def _create_layout(self) -> None:
        """Create the main window layout."""
        # Create menubar first
        self._create_menubar()

        # Main frame
        self.main_frame = ttk.Frame(self.root, padding="5")
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(0, weight=1)

        # Treeview frame with scrollbar
        self.tree_frame = ttk.Frame(self.main_frame)
        self.tree_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 5))
        self.tree_frame.columnconfigure(0, weight=1)
        self.tree_frame.rowconfigure(0, weight=1)

        # Directory treeview with font manager
        # Create the widget that displays the directory hierarchy.
        self.treeview = DirectoryTreeview(self.tree_frame, self._font_manager)
        self.treeview.grid(row=0, column=0, sticky="nsew")

        # Vertical scrollbar
        self.vscrollbar = ttk.Scrollbar(
            self.tree_frame,
            orient="vertical",
            command=self.treeview.yview,
        )
        self.vscrollbar.grid(row=0, column=1, sticky="ns")
        self.treeview.configure(yscrollcommand=self.vscrollbar.set)

        # Horizontal scrollbar
        self.hscrollbar = ttk.Scrollbar(
            self.tree_frame,
            orient="horizontal",
            command=self.treeview.xview,
        )
        self.hscrollbar.grid(row=1, column=0, sticky="ew")
        self.treeview.configure(xscrollcommand=self.hscrollbar.set)

        # Status bar
        self._create_status_bar()

    # Method/function purpose: Create the status bar at the bottom.
    def _create_status_bar(self) -> None:
        """Create the status bar at the bottom."""
        status_font = self._font_manager.get_status_font()

        # Use a frame with custom background for better styling
        self.status_frame = tk.Frame(
            self.main_frame,
            relief="sunken",
            borderwidth=1,
            background="#f0f0f0",
        )
        self.status_frame.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        self.status_frame.columnconfigure(0, weight=1)

        # Path label
        # Create a Tkinter variable that keeps the displayed path text in sync.
        self.path_var = tk.StringVar(value="Ready")
        self.path_label = tk.Label(
            self.status_frame,
            textvariable=self.path_var,
            font=status_font,
            background="#f0f0f0",
            foreground="#333333",
            padx=10,
            pady=4,
        )
        self.path_label.grid(row=0, column=0, sticky="w")

        # Separator
        separator = tk.Frame(
            self.status_frame,
            width=1,
            background="#cccccc",
        )
        separator.grid(row=0, column=1, sticky="ns", padx=5, pady=4)

        # Items count label
        self.items_var = tk.StringVar(value="Items: 0")
        self.items_label = tk.Label(
            self.status_frame,
            textvariable=self.items_var,
            font=status_font,
            background="#f0f0f0",
            foreground="#666666",
            padx=10,
            pady=4,
        )
        self.items_label.grid(row=0, column=2, sticky="e")

        # Separator
        separator2 = tk.Frame(
            self.status_frame,
            width=1,
            background="#cccccc",
        )
        separator2.grid(row=0, column=3, sticky="ns", padx=5, pady=4)

        # Status label
        self.status_var = tk.StringVar(value="")
        self.status_label = tk.Label(
            self.status_frame,
            textvariable=self.status_var,
            font=status_font,
            background="#f0f0f0",
            foreground="#0066cc",
            padx=10,
            pady=4,
        )
        self.status_label.grid(row=0, column=4, sticky="e")

    # Method/function purpose: Set the scanner instance to use for background scans.
    def set_scanner(self, scanner: Scanner) -> None:
        """Set the scanner instance to use for background scans.

        Args:
            scanner: Scanner instance
        """
        # Save the scanner that will be used for background scans.
        self._scanner = scanner
        # Extract cache from scanner if available
        if hasattr(scanner, "_cache"):
            self._cache = scanner._cache

    # Method/function purpose: Set maximum scan depth.
    def set_max_depth(self, depth: int) -> None:
        """Set maximum scan depth.

        Args:
            depth: Maximum recursion depth
        """
        self._max_depth = depth

    # Method/function purpose: Start a background scan of a directory.
    def start_background_scan(
        self,
        path: Path,
        parent_node: Optional[DirNode] = None,
        parent_iid: str = "",
    ) -> None:
        """Start a background scan of a directory.

        Args:
            path: Directory path to scan
            parent_node: Optional parent node in the tree
            parent_iid: Parent item ID in the treeview
        """
        if self._scanner is None:
            raise RuntimeError("Scanner not set. Call set_scanner() first.")

        # Validate path
        # Validate the selected path before starting filesystem work.
        is_valid, error_msg = PathValidator.validate_path(path)
        if not is_valid:
            self._error_handler.show_error("Invalid Path", error_msg or "Unknown error")
            return

        # Check for long path
        if len(str(path)) > PathValidator.MAX_SAFE_PATH_LENGTH:
            self._error_handler.handle_path_too_long(path)

        # Configure scanner with current filter settings
        # Pass the current hidden-file preference to the scanner.
        self._scanner.set_show_hidden(self._show_hidden)

        # Update status
        self.set_path(str(path))
        self.set_status("Scanning...")

        # Store root path for rescan
        self._root_path = path

        # Start the scan in background
        try:
            self._scan_manager.start_scan(path, self._scanner, parent_node)
        except Exception as e:
            self._error_handler.handle_scan_error(path, e, continue_scan=False)

    # Method/function purpose: Schedule periodic checking for scan messages.
    def _schedule_message_check(self) -> None:
        """Schedule periodic checking for scan messages."""
        # Process any scan messages that are already waiting.
        self._check_messages()
        self._after_id = self.root.after(
            self.MESSAGE_CHECK_INTERVAL, self._schedule_message_check
        )

    # Method/function purpose: Check for and process messages from scan threads.
    def _check_messages(self) -> None:
        """Check for and process messages from scan threads."""
        messages = self._scan_manager.get_messages()

        for msg in messages:
            self._process_message(msg)

        # Update status if scans are active
        if self._scan_manager.has_active_scans():
            self.set_status("Scanning...")
        else:
            self.set_status("Ready")

    # Method/function purpose: Process a single scan message.
    def _process_message(self, msg: ScanMessage) -> None:
        """Process a single scan message.

        Args:
            msg: Message from scan thread
        """
        # Choose the UI action based on the type of message received from the worker thread.
        if isinstance(msg, ScanProgress):
            # Update progress display
            self.items_var.set(f"Items: {msg.items_scanned}")

        elif isinstance(msg, ScanComplete):
            # Scan completed - populate treeview
            self._handle_scan_complete(msg)

        elif isinstance(msg, ScanError):
            # Scan error - show in status and handle properly
            self.set_status(f"Error: {msg.error_message}")
            self._error_handler.handle_scan_error(
                msg.path,
                Exception(msg.error_message),
                continue_scan=True,
            )

    # Method/function purpose: Handle scan completion message.
    def _handle_scan_complete(self, msg: ScanComplete) -> None:
        """Handle scan completion message.

        Builds a proper tree structure from recursive scan results.

        Args:
            msg: Completion message with results
        """
        # Calculate max size for percentages (use total size for proper percentages)
        max_size = msg.total_size if msg.total_size > 0 else 1
        self.treeview.set_max_size(max_size)

        # Build node map: path -> DirNode
        # Index nodes by path so parent directories can be found efficiently.
        node_map: dict[Path, DirNode] = {}

        # First pass: create all nodes
        # First create a model node for each successful scan result.
        for result in msg.results:
            if result.error:
                continue

            node = DirNode(
                path=result.path,
                name=result.name,
                is_dir=result.is_dir,
            )
            node.size = result.size if not result.is_dir else 0
            node_map[result.path] = node

        # Create root node if not in results
        root_iid = str(msg.path)
        if msg.path not in node_map:
            root_node = DirNode(
                path=msg.path,
                name=msg.path.name if msg.path.name else str(msg.path),
                is_dir=True,
            )
            root_node.is_expanded = True
            node_map[msg.path] = root_node
            self.treeview.insert_node("", root_node)

        # Second pass: establish parent-child relationships and calculate dir sizes
        # Second connect each node to its parent in the directory tree.
        for path, node in node_map.items():
            if path == msg.path:
                continue  # Skip root

            # Find parent
            parent_path = path.parent
            parent_node = node_map.get(parent_path)

            if parent_node is not None:
                node.parent = parent_node
                parent_node.add_child(node)

                # Add size to parent directory
                if not node.is_dir:
                    parent_node.size += node.size

        # Propagate sizes up the tree (bottom-up)
        # Sort by depth (deepest first) to propagate sizes correctly
        # Process deeper paths first so child sizes can be added to parent directories.
        sorted_paths = sorted(node_map.keys(), key=lambda p: len(p.parts), reverse=True)
        for path in sorted_paths:
            node = node_map[path]
            if node.parent is not None and node.is_dir:
                node.parent.size += node.size

        # Insert nodes into treeview, sorted by current sort mode
        # Collect all nodes to insert
        nodes_to_insert: list[tuple[Path, DirNode]] = []
        for path, node in node_map.items():
            if path == msg.path:
                continue  # Root already inserted
            nodes_to_insert.append((path, node))

        # Sort by depth first (parents before children), then by sort mode
        nodes_to_insert.sort(
            key=lambda item: (len(item[0].parts), self._get_sort_key(item[1]))
        )

        # Insert in sorted order
        for path, node in nodes_to_insert:
            parent_path = path.parent
            parent_iid = str(parent_path)
            self.treeview.insert_node(parent_iid, node)

        # Update root node size
        existing_root = node_map.get(msg.path)
        if isinstance(existing_root, DirNode):
            existing_root.size = msg.total_size
            root_iid = str(msg.path)
            if self.treeview.get_node(root_iid) is not None:
                self.treeview.update_node(root_iid)

        # Update counts
        self.set_item_count(len(msg.results))

    # Method/function purpose: Update the path display in the status bar.
    def set_path(self, path: str) -> None:
        """Update the path display in the status bar.

        Args:
            path: Current path to display
        """
        self.path_var.set(path)

    # Method/function purpose: Update the item count display.
    def set_item_count(self, count: int) -> None:
        """Update the item count display.

        Args:
            count: Number of items
        """
        self.items_var.set(f"Items: {count}")

    # Method/function purpose: Update the status message.
    def set_status(self, status: str) -> None:
        """Update the status message.

        Args:
            status: Status message to display
        """
        self.status_var.set(status)

    # Method/function purpose: Start the main event loop.
    def run(self) -> None:
        """Start the main event loop."""
        self.root.mainloop()

    # Method/function purpose: Clean up resources before destruction.
    def cleanup(self) -> None:
        """Clean up resources before destruction."""
        # Stop all background scans
        # Request all background scans to stop before closing the window.
        self._scan_manager.stop_all()
        # Cancel scheduled after call
        if self._after_id is not None:
            self.root.after_cancel(self._after_id)
            self._after_id = None
        # Close cache connection
        if self._cache is not None:
            self._cache.close()

    # Method/function purpose: Quit the application.
    def quit(self) -> None:
        """Quit the application."""
        self.cleanup()
        self.root.destroy()
