"""User interface components for the Material Combiner addon.

This package contains the UI panels and interface elements for the Material Combiner:
- credits_panel: Developer credits and support links
- main_panel: Primary interface for material combination settings
- property_panel: Material-specific property configuration
- update_panel: Addon update management interface
"""

from . import (
    credits_panel,
    main_panel,
    property_panel,
    selection_menu,
    update_panel,
)

__all__ = [
    "credits_panel",
    "main_panel",
    "property_panel",
    "selection_menu",
    "update_panel",
]
