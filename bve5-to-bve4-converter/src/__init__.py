"""
BVE5 to BVE4 Converter
"""

from .converter import (
    BVE5ToBVE4Converter,
    BVE5StructureConverter,
    BVE5StationConverter,
    ConversionResult,
    detect_file_type
)

__version__ = '1.0.0'
__all__ = [
    'BVE5ToBVE4Converter',
    'BVE5StructureConverter',
    'BVE5StationConverter',
    'ConversionResult',
    'detect_file_type'
]
