"""Material property configuration UI panel.

Provides a dialog operator for displaying and modifying material-specific
settings in the Material Combiner addon. Users can configure texture size
constraints and diffuse color options before combining materials.
"""

from typing import Optional, Set, Tuple

import bpy
from bpy.props import IntProperty

from .. import globs
from ..utils.materials import (
    get_image_from_material,
    get_shader_type,
)

DIALOG_WIDTH_FACTOR = 4
MAX_MATERIAL_NAME_LENGTH = 16


class PropertyMenu(bpy.types.Operator):
    """Dialog operator for material property configuration.

    Displays a popup dialog with per-material settings including texture size
    constraints and diffuse color options. These settings affect how materials
    are processed during atlas generation.
    """

    bl_label = "Material Settings"
    bl_idname = "smc.material_properties"
    bl_description = "Show settings for this material"
    bl_options = {"UNDO", "INTERNAL"}

    list_id = IntProperty(default=0)

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> Set:
        """Display the property dialog when invoked.

        Args:
            context: Current Blender context.
            event: Event that triggered the operator.

        Returns:
            Modal state set indicating dialog should be displayed.
        """
        context.scene.smc_list_id = self.list_id
        dpi = self._get_system_dpi(context)
        return context.window_manager.invoke_props_dialog(
            self, width=dpi * DIALOG_WIDTH_FACTOR
        )

    def check(self, context: bpy.types.Context) -> bool:
        """Validate operator parameters.

        Args:
            context: Current Blender context.

        Returns:
            True to continue with execution.
        """
        return True

    def execute(self, context: bpy.types.Context) -> Set[str]:
        """Execute the operator.

        Args:
            context: Current Blender context.

        Returns:
            Set with 'FINISHED' status.
        """
        return {"FINISHED"}

    def draw(self, context: bpy.types.Context) -> None:
        """Draw the property dialog UI layout.

        Args:
            context: Current Blender context.
        """
        scn = context.scene
        item = scn.smc_ob_data[scn.smc_list_id]

        image = self._get_material_image(item.mat)

        col = self.layout.column(align=True)
        col.scale_y = 1.2

        self._show_material_header(col, item.mat)

        box_col = col.box().column()
        if image:
            self._show_image_size_row(box_col, image)
            box_col.separator()
            self._show_diffuse_color(box_col, item, image)
            box_col.separator()
            self._show_size_settings(box_col, item)
        else:
            self._show_size_row(
                box_col, "Base Color Only", 0, (scn.smc_diffuse_size,) * 2
            )
            box_col.separator()
            self._show_diffuse_color(box_col, item)

        if hasattr(col, "template_popup_confirm"):
            col.separator()
            col.template_popup_confirm(
                "", cancel_text="OK", cancel_default=True
            )

    @staticmethod
    def _get_material_image(
        mat: Optional[bpy.types.Material],
    ) -> Optional[bpy.types.Image]:
        """Extract the primary image from a material.

        Args:
            mat: Material to extract image from.

        Returns:
            The primary image texture from the material or None if not found.
        """
        if not mat:
            return None

        return get_image_from_material(mat)

    @staticmethod
    def _show_material_header(
        col: bpy.types.UILayout, mat: bpy.types.Material
    ) -> None:
        """Display material name and preview icon.

        Args:
            col: UI column to add the display to.
            mat: Material to display.
        """
        col.prop(mat, "name", text="", icon_value=mat.preview.icon_id)

    def _show_image_size_row(
        self, col: bpy.types.UILayout, image: bpy.types.Image
    ) -> None:
        """Display image information with name and dimensions.

        Args:
            col: UI column to add the image display to.
            image: Image to display information for.
        """
        if globs.is_blender_3_plus and not image.preview:
            image.preview_ensure()

        # Truncate image name if too long
        image_name = (
            "{}...".format(image.name[:MAX_MATERIAL_NAME_LENGTH])
            if len(image.name) > MAX_MATERIAL_NAME_LENGTH
            else image.name
        )

        self._show_size_row(col, image_name, image.preview.icon_id, image.size)

    @staticmethod
    def _show_size_row(
        col: bpy.types.UILayout,
        label: str,
        icon: Optional[int],
        size: Tuple[int, int],
    ) -> None:
        """Display item size information in a formatted row.

        Args:
            col: UI column to add the label and size display to.
            label: Label text to display.
            icon: Optional icon identifier to display.
            size: Tuple containing width and height dimensions.
        """
        row = col.row()
        label_col = row.column()
        label_col.label(text=label, icon_value=icon)

        size_col = row.column(align=True)
        size_col.alignment = "RIGHT"
        size_col.label(text="Size: {}x{}px".format(*size))

    def _show_diffuse_color(
        self,
        col: bpy.types.UILayout,
        item: bpy.types.PropertyGroup,
        image: Optional[bpy.types.Image] = None,
    ) -> None:
        """Display diffuse color settings based on a material shader type.

        Shows appropriate color inputs based on the material's shader, handling
        different node configurations across various material types.

        Args:
            col: UI column to add the color settings to.
            item: Material item from the combine list.
            image: Optional texture image from the material.
        """
        mat = item.mat

        if globs.is_blender_legacy:
            col.prop(mat, "smc_diffuse")
            if not mat.smc_diffuse:
                return

            col.prop(mat, "diffuse_color", text="")
            return

        shader = get_shader_type(mat)
        if not shader:
            return

        if image:
            col.prop(mat, "smc_diffuse")
            if not mat.smc_diffuse:
                return

        self._display_shader_color_input(col, mat, shader)

    @staticmethod
    def _display_shader_color_input(
        layout: bpy.types.UILayout, mat: bpy.types.Material, shader: str
    ) -> None:
        """Display the color input appropriate for the specific shader type.

        Args:
            layout: UI layout to add the color input to.
            mat: Material to display color for.
            shader: Material's shader type identifier.
        """
        if not mat.node_tree or not mat.node_tree.nodes:
            return

        nodes = mat.node_tree.nodes

        # For MMD materials
        if shader in ["mmd", "mmdCol"] and "mmd_shader" in nodes:
            layout.prop(
                nodes["mmd_shader"].inputs["Diffuse Color"],
                "default_value",
                text="",
            )

        # For MToon materials
        elif (
            shader in ["mtoon", "mtoonCol"]
            and "Mtoon1PbrMetallicRoughness.BaseColorFactor" in nodes
        ):
            layout.prop(
                nodes["Mtoon1PbrMetallicRoughness.BaseColorFactor"],
                "color",
                text="",
            )

        # For VRM materials
        elif shader in ["vrm", "vrmCol"] and "RGB" in nodes:
            layout.prop(nodes["RGB"].outputs[0], "default_value", text="")

        # For XNALara New materials
        elif shader == "xnalaraNewCol" and "Group" in nodes:
            layout.prop(
                nodes["Group"].inputs["Diffuse"], "default_value", text=""
            )

        # For Principled BSDF and XNALara materials
        elif (
            shader in ["principled", "principledCol", "xnalara", "xnalaraCol"]
            and "Principled BSDF" in nodes
        ):
            layout.prop(
                nodes["Principled BSDF"].inputs["Base Color"],
                "default_value",
                text="",
            )

    @staticmethod
    def _show_size_settings(
        col: bpy.types.UILayout, item: bpy.types.PropertyGroup
    ) -> None:
        """Display texture size constraint settings.

        Args:
            col: UI column to add the size settings to.
            item: Material item from the combine list.
        """
        col.prop(item.mat, "smc_size")
        if item.mat.smc_size:
            col = col.column(align=True)
            col.prop(item.mat, "smc_size_width")
            col.prop(item.mat, "smc_size_height")

    @staticmethod
    def _get_system_dpi(context: bpy.types.Context) -> int:
        """Retrieve system DPI setting for UI scaling.

        Handles version differences in Blender's preferences system.

        Args:
            context: Current Blender context.

        Returns:
            System DPI value for dialog sizing.
        """
        return (
            context.preferences.system.dpi
            if globs.is_blender_modern
            else context.user_preferences.system.dpi
        )
