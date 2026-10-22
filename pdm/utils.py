
"""Helper utilities for PTDU operations."""

from __future__ import annotations


class SizeCalculator:
    """Provides methods to calculate and format file sizes and percentages."""

    # Supported size units and their equivalent values in bytes
    UNITS: list[tuple[str, int]] = [
        ("B", 1),
        ("KB", 1024),
        ("MB", 1024**2),
        ("GB", 1024**3),
        ("TB", 1024**4),
        ("PB", 1024**5),
    ]

    @classmethod
    def format_size(cls, size_bytes: int) -> str:
        """Convert a size in bytes into a readable format.

        Args:
            size_bytes: The size value expressed in bytes.

        Returns:
            A formatted size string, such as "1.5 MB" or "512 B".
        """
        if size_bytes < 0:
            raise ValueError("Size cannot be negative")

        if size_bytes == 0:
            return "0 B"

        # Check the units from largest to smallest to select the best fit
        for unit_name, unit_bytes in reversed(cls.UNITS):
            if size_bytes >= unit_bytes:
                value = size_bytes / unit_bytes

                # Display bytes as integers and larger units with decimals
                if unit_name == "B":
                    return f"{int(value)} {unit_name}"
                elif unit_name == "KB":
                    return f"{value:.1f} {unit_name}"
                else:
                    return f"{value:.2f} {unit_name}"

        return f"{size_bytes} B"

    @classmethod
    def format_percentage(cls, part: int, total: int) -> str:
        """Calculate a percentage and return it as a formatted string.

        Args:
            part: The portion being compared with the total.
            total: The complete value used as the reference.

        Returns:
            The percentage as a string, such as "45.2%".
        """
        if total <= 0:
            return "0.0%"

        # Calculate the portion's share of the total as a percentage
        percentage = (part / total) * 100
        return f"{percentage:.1f}%"

    @classmethod
    def calculate_percentage(cls, part: int, total: int) -> float:
        """Calculate a percentage and return its numeric value.

        Args:
            part: The portion being compared with the total.
            total: The complete value used as the reference.

        Returns:
            The calculated percentage as a floating-point number.
        """
        if total <= 0:
            return 0.0

        # Return the percentage without converting it into a string
        return (part / total) * 100
