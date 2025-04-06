import bpy

from .. import globs
from ..icons import get_icon_id

_GITHUB_README_URL = 'https://github.com/Grim-es/material-combiner-addon/?tab=readme-ov-file#pillow-installation-process-is-repeated'
_DISCORD_CONTACT_URL = 'https://discordapp.com/users/275608234595713024'
_INSTALL_HELP_TEXT = (
    'If the installation process is repeated, try running Blender as Administrator '
    'or check your Internet connection.'
)


class MaterialMenu(bpy.types.Panel):
    bl_label = 'Main Menu'
    bl_idname = 'SMC_PT_Main_Menu'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI' if globs.is_blender_2_80_or_newer else 'TOOLS'
    bl_category = 'MatCombiner'

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout

        if globs.pil_exist:
            self._render_main_interface(context, layout)
        elif globs.smc_pi:
            self.render_install_success(layout)
        else:
            self.draw_pillow_installer(context, layout)

    def _render_main_interface(self, context: bpy.types.Context, layout: bpy.types.UILayout) -> None:
        self._create_materials_list(context, layout)
        self._create_properties_section(context.scene, layout)
        self._create_action_controls(layout)

    @staticmethod
    def _create_materials_list(context: bpy.types.Context, layout: bpy.types.UILayout) -> None:
        scene = context.scene
        column = layout.column(align=True)

        column.label(text='Materials to Combine:') # TODO: Dropdown Menu Select/Deselect All
        column.template_list(
            'SMC_UL_Combine_List',
            'combine_list',
            scene,
            'smc_ob_data',
            scene,
            'smc_ob_data_id',
            rows=12
        )

        action_column = column.column(align=True)
        action_column.scale_y = 1.2
        action_text = 'Update Material List' if scene.smc_ob_data else 'Generate Material List'
        action_column.operator('smc.refresh_ob_data', text=action_text, icon_value=get_icon_id('null'))

    def _create_properties_section(self, scene: bpy.types.Scene, layout: bpy.types.UILayout) -> None:
        column = layout.column()
        column.label(text='Atlas Properties:')

        box = column.box()
        self._add_size_properties(box, scene)
        self._add_quality_properties(box, scene)
        self._add_gap_settings(box, scene)

    @staticmethod
    def _add_size_properties(layout: bpy.types.UILayout, scene: bpy.types.Scene) -> None:
        layout.prop(scene, 'smc_size', text='Atlas Size')

        if scene.smc_size in {'CUST', 'STRICTCUST'}:
            size_col = layout.column(align=True)
            size_col.scale_y = 1.2
            size_col.prop(scene, 'smc_size_width', text='Width')
            size_col.prop(scene, 'smc_size_height', text='Height')

    @staticmethod
    def _add_quality_properties(layout: bpy.types.UILayout, scene: bpy.types.Scene) -> None:
        layout.prop(scene, 'smc_crop', text='Enable Cropping')
        layout.prop(scene, 'smc_pixel_art', text='Pixel Art Mode')

    def _add_gap_settings(self, layout: bpy.types.UILayout, scene: bpy.types.Scene) -> None:
        self._create_property_row(
            layout,
            'smc_diffuse_size',
            'Base Color Size:'
        )

        self._create_property_row(
            layout,
            'smc_gaps',
            'Spacing Between Textures:'
        )

    @staticmethod
    def _create_property_row(layout: bpy.types.UILayout, prop: str, label: str) -> None:
        row = layout.row()
        col = row.column()
        col.scale_y = 1.2
        col.label(text=label)
        col = row.column()
        col.scale_x = 0.75
        col.scale_y = 1.2
        col.alignment = 'RIGHT'
        col.prop(bpy.context.scene, prop, text='')

    @staticmethod
    def _create_action_controls(layout: bpy.types.UILayout) -> None:
        col = layout.column()
        col.scale_y = 1.5
        col.operator(
            'smc.combiner',
            text='Generate Texture Atlas',
            icon_value=get_icon_id('save')
        ).cats = False

    @staticmethod
    def draw_pillow_installer(context: bpy.types.Context, layout: bpy.types.UILayout) -> None:
        box = layout.box()
        MaterialMenu._render_install_header(box)
        MaterialMenu._render_install_actions(box)
        MaterialMenu._render_install_troubleshooting(box, context)

    @staticmethod
    def _render_install_header(layout: bpy.types.UILayout) -> None:
        col = layout.column(align=True)
        col.label(text='Python Imaging Library Required', icon='ERROR')
        col.separator()

    @staticmethod
    def _render_install_actions(layout: bpy.types.UILayout) -> None:
        row = layout.row()
        row.scale_y = 1.5
        row.operator('smc.get_pillow', text='Install Pillow', icon='IMPORT')

    @staticmethod
    def _render_install_troubleshooting(layout: bpy.types.UILayout, context: bpy.types.Context) -> None:
        layout.separator()
        layout.label(text=_INSTALL_HELP_TEXT)

        help_col = layout.column(align=True)
        help_col.scale_y = 1.2
        help_col.operator(
            'smc.browser',
            text='ReadMe on GitHub',
            icon='URL'
        ).link = _GITHUB_README_URL

        help_col.operator(
            'smc.browser',
            text='Contact Support (Discord)',
            icon='COMMUNITY'
        ).link = _DISCORD_CONTACT_URL

    @staticmethod
    def render_install_success(layout: bpy.types.UILayout) -> None:
        box = layout.box().column()
        box.label(text='Installation Complete', icon='CHECKMARK')
        box.label(text='Please Restart Blender', icon='INFO')
