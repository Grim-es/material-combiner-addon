"""Operator implementations for the Material Combiner addon.

This package contains all the operator classes that provide functionality for the addon:
- browser: External web browser integration for documentation and support links
- get_pillow: Dependency installation handling
- combiner: Core material combining functionality
- combine_list: UI-related operators for the material list
"""

from . import browser, get_pillow
from .combiner import combiner
from .ui import combine_list

__all__ = ["browser", "combine_list", "combiner", "get_pillow"]
