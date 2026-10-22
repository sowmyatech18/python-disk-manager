```python
"""Font configuration utility for PTDU.

Detects suitable fonts for the current operating system
and manages font settings used throughout the application.
"""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import font as tkfont
from typing import Literal, Optional


class FontManager:
    """Handles font selection, creation, sizing, and measurement."""

    # Default font sizes used by different parts of the application
    BASE_SIZE: int = 13
    HEADING_SIZE: int = 12
    STATUS_SIZE: int = 12

    # Controls how much the font size changes and its allowed limits
    SIZE_STEP: int = 1
    MIN_SIZE: int = 8
    MAX_SIZE: int = 20

    # Preferred fonts for Linux systems, checked in the given order
    LINUX_FONTS: tuple[str, ...] = (
        "Ubuntu",
        "Noto Sans",
        "DejaVu Sans",
        "Cantarell",
        "Liberation Sans",
    )

    # Preferred fonts for macOS systems
    MACOS_FONTS: tuple[str, ...] = (".SF NS", "Helvetica Neue", "Helvetica", "Arial")

    # Preferred fonts for Windows systems
    WINDOWS_FONTS: tuple[str, ...] = ("Segoe UI", "Tahoma", "Arial")

    def __init__(self, root: Optional[tk.Tk] = None) -> None:
        """Initialize the font manager.

        Args:
            root: Existing Tkinter root window, if available.
        """
        self._root: Optional[tk.Tk] = root
        self._family: Optional[str] = None
        self._fonts: dict[str, tkfont.Font] = {}

    def _get_available_fonts(self) -> set[str]:
        """Retrieve the font families available on the system.

        A temporary Tkinter window is created when no root window
        has been provided.

        Returns:
            A set containing the available font family names.
        """
        if self._root is None:
            # Create a temporary window to query the installed fonts
            temp_root = tk.Tk()
            temp_root.withdraw()
            families = set(tkfont.families(temp_root))
            temp_root.destroy()
        else:
            # Use the existing window to retrieve the font families
            families = set(tkfont.families(self._root))

        return families

    def detect_font_family(self) -> str:
        """Select the first available font preferred for the current OS.

        Returns:
            The selected font family name.
        """
        available = self._get_available_fonts()
        system = sys.platform

        # Choose the font preference list based on the operating system
        if system == "darwin":  # macOS
            preferences = self.MACOS_FONTS
        elif system == "win32":  # Windows
            preferences = self.WINDOWS_FONTS
        else:  # Linux and other platforms
            preferences = self.LINUX_FONTS

        # Return the first preferred font that is installed
        for family in preferences:
            if family in available:
                self._family = family
                return family

        # Use Tkinter's default font if no preferred font is available
        self._family = "TkDefaultFont"
        return self._family

    def get_family(self) -> str:
        """Return the selected font family, detecting it if necessary.

        Returns:
            The selected or default font family name.
        """
        if self._family is None:
            return self.detect_font_family()
        return self._family

    def get_font(
        self,
        name: str,
        size: Optional[int] = None,
        weight: Literal["normal", "bold"] = "normal",
        slant: Literal["roman", "italic"] = "roman",
    ) -> tkfont.Font:
        """Retrieve an existing font or create a new font configuration.

        Args:
            name: Identifier used to store and retrieve the font.
            size: Font size in points; defaults to BASE_SIZE.
            weight: Font thickness, either normal or bold.
            slant: Font style, either roman or italic.

        Returns:
            The configured Tkinter Font object.
        """
        # Reuse the font if this name has already been registered
        if name in self._fonts:
            return self._fonts[name]

        # Get the selected family and determine the font size
        family = self.get_family()
        actual_size = size if size is not None else self.BASE_SIZE

        # Create the font and store it for future use
        font = tkfont.Font(family=family, size=actual_size, weight=weight, slant=slant)
        self._fonts[name] = font

        return font

   
