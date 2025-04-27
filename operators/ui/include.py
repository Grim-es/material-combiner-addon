"""UI integration module for Material Combiner.

This module provides functions to draw the Material Combiner UI within other
addons or UI panels. It handles the main UI parts including the material
list, action buttons, and support links.
"""

import bpy

from ... import globs
from ...icons import get_icon_id
from ...type_annotations import Scene
from ...ui.main_panel import MaterialCombinerPanel


def draw_ui(context: bpy.types.Context, m_col: bpy.types.UILayout) -> None:
    """Draw the Material Combiner UI in the provided layout.

    Args:
        context: Current Blender context.
        m_col: UILayout to draw the Material Combiner interface in.
    """
    if globs.pil_available:
        _materials_list(context.scene, m_col)
    elif globs.pil_install_attempted:
        col = m_col.box().column()
        col.label(text="Installation complete", icon_value=get_icon_id("done"))
        col.label(text="Please restart Blender", icon_value=get_icon_id("null"))
    else:
        MaterialCombinerPanel.pillow_installator(m_col)


def _materials_list(scn: Scene, m_col: bpy.types.UILayout) -> None:
    """Draw the material list and associated UI components.

    Draws the material list template, update button, save atlas button,
    and support links for the addon.

    Args:
        scn: Current Blender scene.
        m_col: UILayout to draw the material list in.
    """
    patreon = "https://www.patreon.com/shotariya"
    buymeacoffee = "https://buymeacoffee.com/shotariya"

    if scn.smc_ob_data:
        m_col.template_list(
            "SMC_UL_Combine_List",
            "combine_list",
            scn,
            "smc_ob_data",
            scn,
            "smc_ob_data_id",
            rows=12,
            type="DEFAULT",
        )
    col = m_col.column(align=True)
    col.scale_y = 1.2
    col.operator(
        "smc.refresh_ob_data",
        text="Update Material List"
        if scn.smc_ob_data
        else "Generate Material List",
        icon_value=get_icon_id("null"),
    )
    col = m_col.column()
    col.scale_y = 1.5
    col.operator(
        "smc.combiner", text="Save Atlas to..", icon_value=get_icon_id("null")
    ).cats = True
    col.separator()
    col = m_col.column()
    col.label(text="If this saved you time:")
    col.operator(
        "smc.browser",
        text="Support Material Combiner",
        icon_value=get_icon_id("patreon"),
    ).link = patreon
    col.operator(
        "smc.browser", text="Buy Me a Coffee", icon_value=get_icon_id("bmc")
    ).link = buymeacoffee
