"""Treeview widget for displaying directory structure with size details."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from ptdu.fonts import FontManager
from ptdu.models import DirNode
from ptdu.utils import SizeCalculator


class DirectoryTreeview(ttk.Treeview):
    """Custom Treeview that displays files and directories with size information."""

    # Column identifiers used to organize the displayed information
    COL_NAME = "name"
    COL_SIZE = "size"
    COL_PERCENT = "percent"
    COL_SIZE_BAR = "size_bar"
    COL_ITEMS = "items"

    # Tags used to apply different styles to files and directories
    TAG_DIRECTORY = "directory"
    TAG_FILE = "file"
    TAG_HIDDEN = "hidden"
    TAG_LARGE_FILE = "large_file"
    TAG_MEDIUM_FILE = "medium_file"
    TAG_SELECTED = "selected"

    # Characters used to represent file sizes visually
    SIZE_BAR_FULL = "█"
    SIZE_BAR_EMPTY = "░"
    SIZE_BAR_WIDTH = 10

    # File size limits used to apply different text colors
    LARGE_FILE_THRESHOLD = 100 * 1024 * 1024  # Files larger than 100 MB
    MEDIUM_FILE_THRESHOLD = 10 * 1024 * 1024  # Files larger than 10 MB

    def __init__(
        self, parent: tk.Widget, font_manager: Optional[FontManager] = None
    ) -> None:
        """Initialize the treeview and configure its appearance.

        Args:
            parent: Widget that contains this treeview.
            font_manager: Optional manager used to control fonts.
        """
        # Define the additional columns displayed beside the name
        columns = (self.COL_SIZE, self.COL_SIZE_BAR, self.COL_PERCENT, self.COL_ITEMS)

        super().__init__(
            parent,
            columns=columns,
            show="tree headings",
            selectmode="browse",
        )

        # Use the provided font manager or create a default one
        self._font_manager: FontManager = (
            font_manager if font_manager is not None else FontManager()
        )

        # Map each treeview item ID to its corresponding DirNode
        self._node_map: dict[str, DirNode] = {}

        # Store the maximum size used to calculate percentages and size bars
        self._current_max_size: int = 0

        # Configure fonts, columns, and item styles
        self._setup_style()
        self._setup_columns()
        self._setup_tags()

    def _setup_columns(self) -> None:
        """Set column headings, alignment, and widths."""
        # Configure the name column, which also displays the tree structure
        self.heading("#0", text="Name", anchor="w")
        self.column("#0", width=400, minwidth=200, stretch=True)

        # Display the size of each file or directory
        self.heading(self.COL_SIZE, text="Size", anchor="e")
        self.column(self.COL_SIZE, width=90, minwidth=70, stretch=False, anchor="e")

        # Display a visual bar representing the item's size
        self.heading(self.COL_SIZE_BAR, text="", anchor="w")
        self.column(
            self.COL_SIZE_BAR, width=100, minwidth=80, stretch=False, anchor="w"
        )

        # Display the item's size as a percentage of the maximum size
        self.heading(self.COL_PERCENT, text="Percent", anchor="e")
        self.column(self.COL_PERCENT, width=70, minwidth=60, stretch=False, anchor="e")

        # Display the number of items contained in each directory
        self.heading(self.COL_ITEMS, text="Items", anchor="e")
        self.column(self.COL_ITEMS, width=60, minwidth=50, stretch=False, anchor="e")

    def _setup_tags(self) -> None:
        """Assign text and background styles to different item types."""
        dir_font = self._font_manager.get_directory_font()
        file_font = self._font_manager.get_file_font()

        # Directories appear in blue with a directory-specific font
        self.tag_configure(
            self.TAG_DIRECTORY,
            foreground="#0066cc",
            font=dir_font,
        )

        # Files use the default text color and a file-specific font
        self.tag_configure(
            self.TAG_FILE,
            foreground="#000000",
            font=file_font,
        )

        # Hidden files and directories appear in gray
        self.tag_configure(
            self.TAG_HIDDEN,
            foreground="#888888",
        )

        # Large files above 100 MB appear in red
        self.tag_configure(
            self.TAG_LARGE_FILE,
            foreground="#cc0000",
        )

        # Medium-sized files above 10 MB appear in orange
        self.tag_configure(
            self.TAG_MEDIUM_FILE,
            foreground="#cc6600",
        )

        # Apply a light blue background to selected items
        self.tag_configure(
            self.TAG_SELECTED,
            background="#d0e8ff",
        )

    def _setup_style(self) -> None:
        """Configure the treeview fonts and row height."""
        style = ttk.Style()
        treeview_font = self._font_manager.get_treeview_font()

        # Calculate row height from the font's height and add extra spacing
        metrics = treeview_font.metrics()
        row_height = metrics["ascent"] + metrics["descent"] + 8

        # Apply the calculated height and font to the treeview
        style.configure(
            "DirectoryTreeview.Treeview",
            rowheight=row_height,
            font=treeview_font,
        )
        style.configure(
            "DirectoryTreeview.Treeview.Heading",
            font=self._font_manager.get_heading_font(),
        )

        # Apply the custom style to this widget
        self.configure(style="DirectoryTreeview.Treeview")

    def _update_style(self) -> None:
        """Reapply the treeview style after a font size change."""
        self._setup_style()

    def _format_size_bar(self, size: int) -> str:
        """Create a visual bar showing the item's size relative to the maximum.

        Args:
            size: Item size in bytes.

        Returns:
            A string containing filled and empty bar characters.
        """
        # Return an empty bar if either size is zero or no maximum is available
        if self._current_max_size <= 0 or size <= 0:
            return self.SIZE_BAR_EMPTY * self.SIZE_BAR_WIDTH

        # Calculate how much of the bar should be filled
        ratio = size / self._current_max_size
        filled = int(ratio * self.SIZE_BAR_WIDTH)
        filled = max(0, min(filled, self.SIZE_BAR_WIDTH))  # Keep within bar limits

        # Fill the remaining positions with empty characters
        empty = self.SIZE_BAR_WIDTH - filled
        return self.SIZE_BAR_FULL * filled + self.SIZE_BAR_EMPTY * empty

    def insert_node(
        self,
        parent_iid: str,
        node: DirNode,
    ) -> str:
        """Insert a directory or file into the treeview.

        Args:
            parent_iid: ID of the parent item; empty string for the root.
            node: DirNode object containing the item's information.

        Returns:
            The unique treeview item ID.
        """
        # Use the item's path as its unique treeview ID
        iid = str(node.path)

        # Add an icon based on whether the item is a file or directory
        display_name = node.name
        if node.is_dir:
            # Use a closed-folder icon for collapsed directories
            if not node.is_expanded:
                display_name = f"📁 {node.name}"
            else:
                display_name = f"📂 {node.name}"
        else:
            display_name = f"📄 {node.name}"

        # Calculate the item's percentage and size bar when a maximum is available
        percent_str = ""
        size_bar = ""
        if self._current_max_size > 0 and node.size > 0:
            percent = SizeCalculator.calculate_percentage(
                node.size, self._current_max_size
            )
            percent_str = f"{percent:.0f}%"
            size_bar = self._format_size_bar(node.size)

        # Prepare the values for the size, bar, percentage, and item-count columns
        values = (
            SizeCalculator.format_size(node.size),
            size_bar,
            percent_str,
            str(node.get_item_count()) if node.is_dir else "",
        )

        # Select the appropriate styling tags for this item
        tags = self._get_tags_for_node(node)

        # Insert the item into the treeview
        try:
            self.insert(
                parent=parent_iid,
                index="end",
                iid=iid,
                text=display_name,
                values=values,
                tags=tags,
                open=node.is_expanded,
            )
        except tk.TclError:
            # If the item already exists, update its displayed information
            self.item(
                iid, text=display_name, values=values, tags=tags, open=node.is_expanded
            )

        # Save the connection between the treeview ID and the original node
        self._node_map[iid] = node

        return iid

    def _get_tags_for_node(self, node: DirNode) -> tuple[str, ...]:
        """Choose styling tags based on the node's type, size, and name.

        Args:
            node: DirNode containing the item's properties.

        Returns:
            A tuple of tags to apply to the item.
        """
        tags: list[str] = []

        # Apply directory styling or file styling with a size-based color
        if node.is_dir:
            tags.append(self.TAG_DIRECTORY)
        else:
            tags.append(self.TAG_FILE)

            # Use red for files above 100 MB and orange for files above 10 MB
            if node.size > self.LARGE_FILE_THRESHOLD:
                tags.append(self.TAG_LARGE_FILE)
            elif node.size > self.MEDIUM_FILE_THRESHOLD:
                tags.append(self.TAG_MEDIUM_FILE)

        # Treat names beginning with a dot as hidden files or directories
        if node.name.startswith("."):
            tags.append(self.TAG_HIDDEN)

        return tuple(tags)

    def get_node(self, iid: str) -> Optional[DirNode]:
        """Retrieve the DirNode associated with a treeview item ID.

        Args:
            iid: ID of the treeview item.

        Returns:
            The associated DirNode, or None if the ID is not found.
        """
        # Look up the node in the internal ID-to-node mapping
        return self._node_map.get(iid)

    def delete_node(self, iid: str) -> None:
        """Delete a treeview item and remove its mapping.

        Args:
            iid: ID of the item to delete.
        """
        # Remove the item from the visible treeview
        self.delete(iid)
        # Remove its reference from the internal mapping
        self._node_map.pop(iid, None)

    def clear(self) -> None:
        """Remove all root-level items and reset the stored data."""
        # Delete each root item; its descendants are removed with it
        for item in self.get_children():
            self.delete(item)
        # Clear the node mapping and reset the maximum size
        self._node_map.clear()
        self._current_max_size = 0

    def update_node(self, iid: str) -> None:
        """Refresh the displayed information for an existing item.

        Args:
            iid: ID of the item to update.
        """
        # Retrieve the node; stop if the ID has no associated node
        node = self._node_map.get(iid)
        if node is None:
            return

        # Update the icon and displayed name based on the item's current state
        display_name = node.name
        if node.is_dir:
            if not node.is_expanded:
                display_name = f"📁 {node.name}"
            else:
                display_name = f"📂 {node.name}"
        else:
            display_name = f"📄 {node.name}"

        # Recalculate the percentage and size bar using the current maximum
        percent_str = ""
        size_bar = ""
        if self._current_max_size > 0 and node.size > 0:
            percent = SizeCalculator.calculate_percentage(
                node.size, self._current_max_size
            )
            percent_str = f"{percent:.0f}%"
            size_bar = self._format_size_bar(node.size)

        # Prepare the updated values for all additional columns
        values = (
            SizeCalculator.format_size(node.size),
            size_bar,
            percent_str,
            str(node.get_item_count()) if node.is_dir else "",
        )

        # Recalculate the styling tags in case the node's properties changed
        tags = self._get_tags_for_node(node)

        # Update the item's name, values, styling, and expanded state
        self.item(
            iid, text=display_name, values=values, tags=tags, open=node.is_expanded
        )

    def set_max_size(self, max_size: int) -> None:
        """Set the reference size used for percentage and bar calculations.

        Args:
            max_size: Maximum size in bytes.
        """
        self._current_max_size = max_size

    def get_selected_node(self) -> Optional[DirNode]:
        """Return the DirNode corresponding to the currently selected item."""
        # Get the selected item IDs
        selection = self.selection()
        if not selection:
            return None
        # Return the node associated with the first selected item
        return self._node_map.get(selection[0])

    def select_node(self, iid: str) -> None:
        """Select an item, move focus to it, and bring it into view.

        Args:
            iid: ID of the item to select.
        """
        self.selection_set(iid)
        self.focus(iid)
        self.see(iid)


