
"""PTDU - Python Tkinter Disk Usage Analyzer.

This package provides tools to scan directories, represent files and folders
as a tree, and display disk usage through a graphical interface.
"""

# Current version of the PTDU application
__version__ = "0.1.0"


# Import the cache module to reuse previously obtained scan results
from ptdu.cache import ScanCache

# Import classes and functions for error handling and path validation
from ptdu.errors import ErrorHandler, PathValidator, get_error_handler

# Import the font manager used to manage fonts in the user interface
from ptdu.fonts import FontManager

# Import DirNode, which represents each file or directory in a tree
from ptdu.models import DirNode

# Import tools that help improve performance and manage memory usage
from ptdu.performance import (
    LargeDirectoryHandler,       # Handles directories with many entries
    MemoryOptimizer,             # Helps optimize memory consumption
    VirtualScroller,             # Supports scrolling through large data views
    estimate_directory_size,     # Estimates directory size
)

# Import functions and classes used to scan the filesystem
from ptdu.scanner import (
    MemoryMonitor,               # Monitors memory usage
    Scanner,                     # Scans files and directories
    ScanResult,                  # Represents the result of a scan
    get_system_info,             # Retrieves system information
)

# Import the class that displays files and folders in a tree view
from ptdu.treeview import DirectoryTreeview

# Import the main window of the graphical application
from ptdu.ui import MainWindow

# Import the utility used to calculate and format file sizes
from ptdu.utils import SizeCalculator


# Define the public classes and functions of the PTDU package.
# These names are included when using: from ptdu import *
__all__ = [
    "DirNode",                  # Represents a file or directory node
    "DirectoryTreeview",        # Displays the directory tree
    "ErrorHandler",             # Handles application errors
    "FontManager",              # Manages application fonts
    "LargeDirectoryHandler",    # Handles large directories
    "MainWindow",               # Main graphical application window
    "MemoryMonitor",            # Monitors memory usage
    "MemoryOptimizer",          # Helps manage memory usage
    "PathValidator",            # Validates filesystem paths
    "ScanCache",                # Stores reusable scan results
    "ScanResult",               # Stores scan result information
    "Scanner",                  # Scans directories and files
    "SizeCalculator",           # Calculates and formats file sizes
    "VirtualScroller",          # Supports scrolling through large data
    "estimate_directory_size",  # Estimates directory size
    "get_error_handler",        # Returns the error handler
    "get_system_info",          # Retrieves system information
]
