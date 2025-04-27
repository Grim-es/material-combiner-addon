"""Icon management system for the Material Combiner addon.

This module provides functions to load and manage icons used throughout the addon UI.
It handles the creation, access, and cleanup of Blender preview icons.
"""

import os
from typing import cast

import bpy
import bpy.utils.previews

from ..type_annotations import SMCIcons

smc_icons = cast(SMCIcons, None)
icons_directory = os.path.dirname(__file__)


def get_icon_id(identifier: str) -> int:
    """Get the icon ID for a given identifier.

    Args:
        identifier: Icon name without extension

    Returns:
        Blender icon ID to use in UI elements
    """
    return get_icon(identifier).icon_id


def get_icon(identifier: str) -> bpy.types.ImagePreview:
    """Get the icon preview object for a given identifier.

    Loads the icon if not already loaded.

    Args:
        identifier: Icon name without extension

    Returns:
        Blender image preview object
    """
    if identifier in smc_icons:
        return smc_icons[identifier]
    return smc_icons.load(
        identifier,
        os.path.join(icons_directory, "{}.png".format(identifier)),
        "IMAGE",
    )


def initialize_smc_icons() -> None:
    """Initialize the icon preview collection.

    Must be called during addon registration before using any icon functions.
    """
    global smc_icons
    smc_icons = bpy.utils.previews.new()


def unload_smc_icons() -> None:
    """Remove the icon preview collection.

    Should be called during addon unregistration to free resources.
    """
    bpy.utils.previews.remove(smc_icons)
