
"""Entry point for the PTDU application.

This file handles command-line arguments, validates the directory,
configures the scanner and cache, and starts the graphical interface.
"""

# Used to create and handle command-line arguments
import argparse

# Used to exit the program and print error messages
import sys

# Used to work with filesystem paths
from pathlib import Path

# Import the class that manages cached scan results
from ptdu.cache import ScanCache

# Import the class that scans files and directories
from ptdu.scanner import Scanner

# Import the main graphical application window
from ptdu.ui import MainWindow


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure command-line arguments."""

    # Create the argument parser with the program's name and description
    parser = argparse.ArgumentParser(
        prog="ptdu",
        description="Python Tkinter Disk Usage analyzer - A graphical disk usage tool",
        epilog="Keyboard shortcuts: j/k=navigate, h/l=expand/collapse, q=quit, r=rescan, d=delete",
    )

    # Accept an optional directory path; use the current directory by default
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        type=Path,
        help="Directory to analyze (default: current directory)",
    )

    # Enable scanning through symbolic links when this flag is provided
    parser.add_argument(
        "--follow-symlinks",
        action="store_true",
        help="Follow symbolic links when scanning",
    )

    # Allow users to specify additional file or directory exclusion patterns
    # The option can be supplied multiple times
    parser.add_argument(
        "--exclude",
        "-e",
        action="append",
        default=[],
        help="Additional patterns to exclude (can be used multiple times)",
    )

    # Set the maximum directory scanning depth
    # If not specified, the depth is unlimited
    parser.add_argument(
        "--max-depth",
        "-d",
        type=int,
        default=None,
        help="Maximum scan depth (default: unlimited)",
    )

    # Disable SQLite caching when this flag is provided
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable SQLite caching",
    )

    # Clear previously stored scan results before starting
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear cache before starting",
    )

    # Display the program version and exit
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    # Return the configured parser
    return parser


def validate_path(path: Path) -> Path:
    """Check that the given path exists and points to a directory."""

    # Stop execution if the path does not exist
    if not path.exists():
        raise SystemExit(f"Error: Path does not exist: {path}")

    # Stop execution if the path is not a directory
    if not path.is_dir():
        raise SystemExit(f"Error: Path is not a directory: {path}")

    # Return the absolute, resolved path
    return path.resolve()


def main() -> int:
    """Configure and start the PTDU application."""

    # Create the parser and read the user's command-line arguments
    parser = create_argument_parser()
    args = parser.parse_args()

    # Validate the directory provided by the user
    try:
        target_path = validate_path(args.path)
    except SystemExit as e:
        # Print validation errors to the standard error stream
        print(str(e), file=sys.stderr)
        return 1

    # Initialize the cache as None by default
    cache: ScanCache | None = None

    # Create a cache unless caching has been disabled
    if not args.no_cache:
        cache = ScanCache()

        # Clear existing cached data if requested
        if args.clear_cache:
            cache.clear()
            print("Cache cleared.")

    # Convert exclusion patterns from a list to a tuple
    # Use None if no exclusion patterns were provided
    exclude_patterns = tuple(args.exclude) if args.exclude else None

    # Create the scanner with the selected configuration options
    scanner = Scanner(
        follow_symlinks=args.follow_symlinks,
        exclude_patterns=exclude_patterns,
        cache=cache,
    )

    # Create the main graphical window
    window = MainWindow()

    # Connect the scanner to the graphical interface
    window.set_scanner(scanner)

    # Configure the maximum scan depth if the user specified one
    if args.max_depth is not None:
        window.set_max_depth(args.max_depth)

    # Start scanning the selected directory in the background
    window.start_background_scan(target_path)

    # Display the application and start its main event loop
    window.run()

    # Return 0 to indicate successful completion
    return 0


# Execute main() only when this file is run directly
# When imported as a module, this block will not execute
if __name__ == "__main__":
    sys.exit(main())
