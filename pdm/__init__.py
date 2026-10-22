
"""PTDU - Python Tkinter Disk Usage Analyzer."""

# Current version of the PTDU application
__version__ = "0.1.0"

# Import the classes and functions required by the application
# from their respective modules.

# Handles caching of directory scan results
from ptdu.cache import ScanCache

# Handles errors, validates paths, and provides the error handler
from ptdu.errors import ErrorHandler, PathValidator, get_error_handler

# Manages fonts used in the graphical user interface
from ptdu.fonts import FontManager

# Represents files and directories as nodes in a tree data structure
from ptdu.models import DirNode

# Provides performance and memory optimization tools
from ptdu.performance import (
    LargeDirectoryHandler,       # Handles directories containing many entries
    MemoryOptimizer,             # Helps optimize memory usage
    VirtualScroller,             # Supports scrolling through large data views
    estimate_directory_size,     # Estimates the size of a directory
)

# Provides filesystem scanning and system information utilities
from ptdu.scanner import (
    MemoryMonitor,               # Monitors memory usage
    Scanner,                     # Scans files and directories
    ScanResult,                  # Stores information about a scanned entry
    get_system_info,             # Retrieves system information
)

# Displays directory information in a graphical tree view
from ptdu.treeview import DirectoryTreeview

# Provides the main application window and user interface
from ptdu.ui import MainWindow

# Calculates and formats file sizes
from ptdu.utils import SizeCalculator


# Defines the public names available when importing everything
# from the ptdu package using: from ptdu import *
__all__ = [
    "DirNode",                  # Tree node model
    "DirectoryTreeview",        # Graphical directory tree
    "ErrorHandler",             # Error handling
    "FontManager",              # Font management
    "LargeDirectoryHandler",    # Large-directory handling
    "MainWindow",               # Main application window
    "MemoryMonitor",             # Memory monitoring
    "MemoryOptimizer",          # Memory optimization
    "PathValidator",             # Path validation
    "ScanCache",                 # Scan result caching
    "ScanResult",                # Scanned entry data
    "Scanner",                   # Filesystem scanning
    "SizeCalculator",             # File size calculations
    "VirtualScroller",           # Scrolling large data views
    "estimate_directory_size",  # Directory size estimation
    "get_error_handler",         # Access the error handler
    "get_system_info",           # Retrieve system information
]
