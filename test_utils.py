
"""Unit tests for the PTDU utility module."""

import pytest

from ptdu.utils import SizeCalculator


class TestSizeCalculator:
    """Tests for the SizeCalculator utility class."""

    class TestFormatSize:
        """Tests for converting byte values into readable size strings."""

        def test_format_zero_bytes(self) -> None:
            """Verify that zero bytes are formatted correctly."""
            assert SizeCalculator.format_size(0) == "0 B"

        def test_format_bytes(self) -> None:
            """Verify formatting for small byte values."""
            assert SizeCalculator.format_size(1) == "1 B"
            assert SizeCalculator.format_size(512) == "512 B"
            assert SizeCalculator.format_size(1023) == "1023 B"

        def test_format_kilobytes(self) -> None:
            """Verify formatting for values expressed in kilobytes."""
            assert SizeCalculator.format_size(1024) == "1.0 KB"
            assert SizeCalculator.format_size(1536) == "1.5 KB"
            assert SizeCalculator.format_size(10240) == "10.0 KB"

        def test_format_megabytes(self) -> None:
            """Verify formatting for values expressed in megabytes."""
            assert SizeCalculator.format_size(1024**2) == "1.00 MB"
            assert SizeCalculator.format_size(5 * 1024**2) == "5.00 MB"
            assert SizeCalculator.format_size(1536 * 1024) == "1.50 MB"

        def test_format_gigabytes(self) -> None:
            """Verify formatting for values expressed in gigabytes."""
            assert SizeCalculator.format_size(1024**3) == "1.00 GB"
            assert SizeCalculator.format_size(int(1.5 * 1024**3)) == "1.50 GB"

        def test_format_terabytes(self) -> None:
            """Verify formatting for values expressed in terabytes."""
            assert SizeCalculator.format_size(1024**4) == "1.00 TB"

        def test_format_petabytes(self) -> None:
            """Verify formatting for values expressed in petabytes."""
            assert SizeCalculator.format_size(1024**5) == "1.00 PB"

        def test_format_negative_raises(self) -> None:
            """Verify that negative sizes raise a ValueError."""
            with pytest.raises(ValueError, match="Size cannot be negative"):
                SizeCalculator.format_size(-1)

    class TestFormatPercentage:
        """Tests for calculating percentages and formatting them as strings."""

        def test_format_zero_total(self) -> None:
            """Verify that a zero total produces a zero percentage."""
            assert SizeCalculator.format_percentage(100, 0) == "0.0%"
            assert SizeCalculator.format_percentage(0, 0) == "0.0%"

        def test_format_full_percentage(self) -> None:
            """Verify that a complete portion is formatted as 100 percent."""
            assert SizeCalculator.format_percentage(100, 100) == "100.0%"

        def test_format_partial_percentage(self) -> None:
            """Verify formatting for different partial percentage values."""
            assert SizeCalculator.format_percentage(25, 100) == "25.0%"
            assert SizeCalculator.format_percentage(33, 100) == "33.0%"
            assert SizeCalculator.format_percentage(1, 3) == "33.3%"

        def test_format_small_percentage(self) -> None:
            """Verify formatting for a small percentage value."""
            assert SizeCalculator.format_percentage(1, 1000) == "0.1%"

    class TestCalculatePercentage:
        """Tests for calculating percentages as numeric values."""

        def test_calculate_zero_total(self) -> None:
            """Verify that a zero total returns 0.0."""
            assert SizeCalculator.calculate_percentage(100, 0) == 0.0
            assert SizeCalculator.calculate_percentage(0, 0) == 0.0

        def test_calculate_full_percentage(self) -> None:
            """Verify that the full portion produces 100 percent."""
            assert SizeCalculator.calculate_percentage(100, 100) == 100.0

        def test_calculate_partial_percentage(self) -> None:
            """Verify calculations for partial percentage values."""
            assert SizeCalculator.calculate_percentage(25, 100) == 25.0
            assert SizeCalculator.calculate_percentage(1, 4) == 25.0

        def test_calculate_returns_float(self) -> None:
            """Verify that the calculated percentage is a float."""
            result = SizeCalculator.calculate_percentage(50, 100)
            assert isinstance(result, float)
