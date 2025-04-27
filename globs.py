"""Global constants and configuration for the Material Combiner addon.

This module contains version detection logic, global constants, and configuration
variables used throughout the addon. It provides consistent access to version-specific
features and establishes addon-wide settings.
"""

import importlib.util
import site
import sys

import bpy

sys.path.insert(0, site.getusersitepackages())

pil_available = all(
    importlib.util.find_spec(module) is not None
    for module in ("PIL", "PIL.Image", "PIL.ImageChops")
)

pil_install_attempted = False

is_blender_legacy = bpy.app.version < (2, 80, 0)
is_blender_modern = bpy.app.version >= (2, 80, 0)
is_blender_2_92_plus = bpy.app.version >= (2, 92, 0)
is_blender_3_plus = bpy.app.version >= (3, 0, 0)

ICON_OBJECT = "META_CUBE" if is_blender_modern else "VIEW3D"
ICON_PROPERTIES = "PREFERENCES" if is_blender_modern else "SCRIPT"
ICON_DROPDOWN = "THREE_DOTS" if is_blender_modern else "DOWNARROW_HLT"


class CombineListTypes:
    """Constants for material combination list entry types.

    These constants are used to identify the type of entry in the
    material combination list UI. They determine how entries are
    displayed, processed, and interacted with.
    """

    OBJECT = 0
    MATERIAL = 1
    SEPARATOR = 2
