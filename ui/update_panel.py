"""UI panel for displaying and managing addon updates.

This module provides a panel in the Blender UI for checking, configuring,
and installing updates for the Material Combiner addon.
"""

import bpy

from .. import addon_updater_ops, globs


class UpdatePanel(bpy.types.Panel):
    """Panel for managing addon updates.

    This class implements a Blender panel that provides functionality for
    checking, configuring, and installing updates for the Material Combiner addon,
    using the addon updater API.
    """

    bl_label = "Updates"
    bl_idname = "SMC_PT_Update_Panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI" if globs.is_blender_modern else "TOOLS"
    bl_category = "MatCombiner"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context: bpy.types.Context) -> None:
        """Draw the panel layout with updater UI elements.

        Args:
            context: The current Blender context.
        """
        addon_updater_ops.update_settings_ui(self, context)
