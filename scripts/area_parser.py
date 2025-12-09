"""
=============================================================================
ArchiText: Area Unit Parser
=============================================================================

This module handles parsing of area specifications in various measurement units
commonly used in real estate, particularly in Pakistan and India. It serves as
a preprocessing component for the Bounded Layout Generator.

Integration in ArchiText Pipeline:
----------------------------------
    User Input (e.g., "5 marla house")
        → Area Parser (this module)
        → AreaBounds object
        → Bounded Layout Generator
        → GraphLayoutOptimizer
        → BIM Generator

Supported Area Units:
---------------------
    Pakistani/Indian (commonly used in South Asian real estate):
        - marla:  1 marla = 272.25 sq ft = 25.29 sqm
                  Common in residential plots (5, 7, 10 marla houses)
        - kanal:  1 kanal = 20 marla = 505.86 sqm
                  Used for larger properties

    Imperial (US/UK measurements):
        - sq ft, square feet, sqft
        - WxH feet (e.g., "60x80 feet" for a 60ft by 80ft plot)

    Metric (International standard):
        - sq m, sqm, m², square meters
        - WxH meters (e.g., "20x25 meters")

Parsing Strategy:
-----------------
    1. Dimension patterns (WxH) are checked first as they're most specific
    2. Area-only patterns are then checked (marla, kanal, sqft, sqm)
    3. For area-only specs, dimensions are computed using default aspect ratio
       (1:1.5, typical for South Asian residential plots)

Example Usage:
--------------
    >>> parser = AreaParser()
    >>> bounds = parser.parse("5 marla")
    >>> print(f"{bounds.width:.1f}m x {bounds.height:.1f}m")  # ~9.1m x 13.9m
    >>> print(f"{bounds.area_sqm:.1f} sqm")  # ~126.5 sqm

Author: ArchiText Team
Version: 1.0.0
=============================================================================
"""

import re
from typing import Tuple, Optional, Dict, Union
from dataclasses import dataclass


@dataclass
class AreaBounds:
    """Represents area bounds in square meters."""
    width: float  # meters
    height: float  # meters
    area_sqm: float  # square meters
    original_spec: str
    unit: str

    @property
    def area_sqft(self) -> float:
        return self.area_sqm * 10.764

    @property
    def area_marla(self) -> float:
        return self.area_sqm / 25.2929  # 1 marla = 25.2929 sqm

    @property
    def area_kanal(self) -> float:
        return self.area_sqm / 505.857  # 1 kanal = 20 marla = 505.857 sqm


class AreaParser:
    """
    Parse area specifications from natural language or structured input.

    Supported formats:
    - "5 marla", "5 marlas"
    - "1 kanal", "2 kanals"
    - "2000 sq ft", "2000 square feet", "2000sqft"
    - "200 sq m", "200 square meters", "200m2", "200 sqm"
    - "60x80 feet", "60 x 80 ft", "60ft x 80ft"
    - "20x25 meters", "20 x 25 m", "20m x 25m"
    - "60' x 80'" (feet with apostrophe)
    """

    # Conversion factors to square meters
    CONVERSIONS = {
        'sqm': 1.0,
        'sqft': 0.0929,  # 1 sq ft = 0.0929 sqm
        'marla': 25.2929,  # 1 marla = 272.25 sq ft = 25.2929 sqm
        'kanal': 505.857,  # 1 kanal = 20 marla = 505.857 sqm
    }

    # Default aspect ratios for area-only specs (width:height)
    # Typical plot ratios in Pakistan are around 1:1.5 to 1:2
    DEFAULT_ASPECT_RATIO = 1.5

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for area parsing."""

        # Dimension patterns (WxH)
        self.dim_feet_pattern = re.compile(
            r"(\d+(?:\.\d+)?)\s*(?:ft|feet|foot|'|f)?\s*[xX×]\s*(\d+(?:\.\d+)?)\s*(?:ft|feet|foot|'|f)?",
            re.IGNORECASE
        )
        self.dim_meters_pattern = re.compile(
            r"(\d+(?:\.\d+)?)\s*(?:m|meters?|metres?)?\s*[xX×]\s*(\d+(?:\.\d+)?)\s*(?:m|meters?|metres?)?",
            re.IGNORECASE
        )

        # Area patterns
        self.marla_pattern = re.compile(
            r"(\d+(?:\.\d+)?)\s*marla?s?",
            re.IGNORECASE
        )
        self.kanal_pattern = re.compile(
            r"(\d+(?:\.\d+)?)\s*kanals?",
            re.IGNORECASE
        )
        self.sqft_pattern = re.compile(
            r"(\d+(?:\.\d+)?)\s*(?:sq\.?\s*(?:ft|feet|foot)|square\s*(?:ft|feet|foot)|sqft|sf)",
            re.IGNORECASE
        )
        self.sqm_pattern = re.compile(
            r"(\d+(?:\.\d+)?)\s*(?:sq\.?\s*(?:m|meters?|metres?)|square\s*(?:m|meters?|metres?)|sqm|m2|m²)",
            re.IGNORECASE
        )

    def parse(self, spec: str) -> Optional[AreaBounds]:
        """
        Parse an area specification string into AreaBounds.

        Args:
            spec: Area specification string

        Returns:
            AreaBounds object or None if parsing fails
        """
        spec = spec.strip()

        # Try dimension patterns first (more specific)
        result = self._try_parse_dimensions(spec)
        if result:
            return result

        # Try area patterns
        result = self._try_parse_area(spec)
        if result:
            return result

        return None

    def _try_parse_dimensions(self, spec: str) -> Optional[AreaBounds]:
        """Try to parse WxH dimension format."""

        # Check if it explicitly mentions feet
        has_feet = any(x in spec.lower() for x in ['ft', 'feet', 'foot', "'"])
        has_meters = any(x in spec.lower() for x in ['m', 'meter', 'metre'])

        # Try feet pattern
        match = self.dim_feet_pattern.search(spec)
        if match and (has_feet or not has_meters):
            w_ft = float(match.group(1))
            h_ft = float(match.group(2))
            w_m = w_ft * 0.3048
            h_m = h_ft * 0.3048
            return AreaBounds(
                width=w_m,
                height=h_m,
                area_sqm=w_m * h_m,
                original_spec=spec,
                unit='feet'
            )

        # Try meters pattern
        match = self.dim_meters_pattern.search(spec)
        if match:
            w_m = float(match.group(1))
            h_m = float(match.group(2))
            return AreaBounds(
                width=w_m,
                height=h_m,
                area_sqm=w_m * h_m,
                original_spec=spec,
                unit='meters'
            )

        return None

    def _try_parse_area(self, spec: str) -> Optional[AreaBounds]:
        """Try to parse area-only format (convert to dimensions using aspect ratio)."""

        area_sqm = None
        unit = None

        # Try kanal first (larger unit)
        match = self.kanal_pattern.search(spec)
        if match:
            kanals = float(match.group(1))
            area_sqm = kanals * self.CONVERSIONS['kanal']
            unit = 'kanal'

        # Try marla
        if not area_sqm:
            match = self.marla_pattern.search(spec)
            if match:
                marlas = float(match.group(1))
                area_sqm = marlas * self.CONVERSIONS['marla']
                unit = 'marla'

        # Try sq ft
        if not area_sqm:
            match = self.sqft_pattern.search(spec)
            if match:
                sqft = float(match.group(1))
                area_sqm = sqft * self.CONVERSIONS['sqft']
                unit = 'sqft'

        # Try sq m
        if not area_sqm:
            match = self.sqm_pattern.search(spec)
            if match:
                sqm = float(match.group(1))
                area_sqm = sqm
                unit = 'sqm'

        if area_sqm:
            # Convert area to dimensions using default aspect ratio
            # area = width * height = width * (width * aspect_ratio)
            # area = width^2 * aspect_ratio
            # width = sqrt(area / aspect_ratio)
            import math
            width = math.sqrt(area_sqm / self.DEFAULT_ASPECT_RATIO)
            height = width * self.DEFAULT_ASPECT_RATIO

            return AreaBounds(
                width=width,
                height=height,
                area_sqm=area_sqm,
                original_spec=spec,
                unit=unit
            )

        return None

    def parse_with_dimensions(self, spec: str,
                              width: Optional[float] = None,
                              height: Optional[float] = None,
                              unit: str = 'meters') -> Optional[AreaBounds]:
        """
        Parse area with explicit dimension overrides.

        Args:
            spec: Area specification (can be empty if dimensions provided)
            width: Optional explicit width
            height: Optional explicit height
            unit: Unit for dimensions ('meters' or 'feet')
        """
        if width and height:
            if unit == 'feet':
                w_m = width * 0.3048
                h_m = height * 0.3048
            else:
                w_m = width
                h_m = height

            return AreaBounds(
                width=w_m,
                height=h_m,
                area_sqm=w_m * h_m,
                original_spec=spec or f"{width}x{height} {unit}",
                unit=unit
            )

        return self.parse(spec)


def format_area_info(bounds: AreaBounds) -> str:
    """Format area bounds as human-readable string."""
    lines = [
        f"Area Specification: {bounds.original_spec}",
        f"Dimensions: {bounds.width:.1f}m x {bounds.height:.1f}m",
        f"           ({bounds.width/0.3048:.1f}ft x {bounds.height/0.3048:.1f}ft)",
        f"Total Area: {bounds.area_sqm:.1f} sq m",
        f"           {bounds.area_sqft:.0f} sq ft",
        f"           {bounds.area_marla:.1f} marla",
        f"           {bounds.area_kanal:.2f} kanal",
    ]
    return "\n".join(lines)


# Quick test
if __name__ == "__main__":
    parser = AreaParser()

    test_specs = [
        "5 marla",
        "10 marlas",
        "1 kanal",
        "2 kanals",
        "2000 sq ft",
        "2000 square feet",
        "200 sq m",
        "200 sqm",
        "200 m2",
        "60x80 feet",
        "60 x 80 ft",
        "60ft x 80ft",
        "20x25 meters",
        "20 x 25 m",
        "20m x 25m",
        "60' x 80'",
    ]

    print("=" * 60)
    print("AREA PARSER TEST")
    print("=" * 60)

    for spec in test_specs:
        result = parser.parse(spec)
        if result:
            print(f"\n[OK] '{spec}'")
            print(f"     {result.width:.1f}m x {result.height:.1f}m = {result.area_sqm:.1f} sqm")
            print(f"     ({result.area_sqft:.0f} sqft, {result.area_marla:.1f} marla)")
        else:
            print(f"\n[!!] Failed to parse: '{spec}'")
