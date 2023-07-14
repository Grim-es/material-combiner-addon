from typing import Set
from typing import Tuple

import bpy
from bpy.props import IntProperty

from .. import globs
from ..utils.images import get_image
from ..utils.materials import shader_type
from ..utils.textures import get_texture


class PropertyMenu(bpy.types.Operator):
    bl_label = 'Settings for material:'
    bl_idname = 'smc.property_menu'
    bl_description = 'Show settings for this material'
    bl_options = {'UNDO', 'INTERNAL'}

    list_id = IntProperty(default=0)

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> Set:
        scn = context.scene
        dpi = bpy.context.preferences.system.dpi if globs.is_blender_2_80_or_newer else bpy.context.user_preferences.system.dpi
        wm = context.window_manager
        scn.smc_list_id = self.list_id
        return wm.invoke_props_dialog(self, width=dpi * 4)

    def check(self, context: bpy.types.Context) -> bool:
        return True

    def execute(self, context: bpy.types.Context) -> Set[str]:
        return {'FINISHED'}

    def draw(self, context: bpy.types.Context) -> None:
        scn = context.scene
        item = scn.smc_ob_data[scn.smc_list_id]
        if globs.is_blender_2_80_or_newer:
            image = None
            shader = shader_type(item.mat) if item.mat else None
            if shader == 'mmd':
                image = item.mat.node_tree.nodes['mmd_base_tex'].image
            elif shader in ['vrm', 'xnalara', 'diffuse', 'emission']:
                image = item.mat.node_tree.nodes['Image Texture'].image
        else:
            image = get_image(get_texture(item.mat))
        layout = self.layout
        col = layout.column()
        col.scale_y = 1.2
        col.prop(item.mat, 'name', text='', icon_value=item.mat.preview.icon_id)
        if image:
            self._draw_image(col, item, image.size)
        else:
            col.label(text='Image size: {0}x{0}px'.format(scn.smc_diffuse_size))
            col.separator()
            self._draw_diffuse_color(col, item)

    def _draw_image(self, col: bpy.types.UILayout, item: bpy.types.PropertyGroup, size: Tuple[int, int]) -> None:
        col.label(text='Image size: {0}x{1}px'.format(*size))
        col.separator()
        col.prop(item.mat, 'smc_diffuse')
        if item.mat.smc_diffuse:
            self._draw_diffuse_color(col, item)
            col.separator()
        col.prop(item.mat, 'smc_size')
        if item.mat.smc_size:
            col.prop(item.mat, 'smc_size_width')
            col.prop(item.mat, 'smc_size_height')
            col.separator()

    @staticmethod
    def _draw_diffuse_color(col: bpy.types.UILayout, item: bpy.types.PropertyGroup) -> None:
        if globs.is_blender_2_79_or_older:
            col.prop(item.mat, 'diffuse_color', text='')
            return

        shader = shader_type(item.mat)
        if shader in ['mmd', 'mmdCol']:
            col.prop(item.mat.node_tree.nodes['mmd_shader'].inputs['Diffuse Color'], 'default_value', text='')
        elif shader in ['vrm', 'vrmCol']:
            col.prop(item.mat.node_tree.nodes['RGB'].outputs[0], 'default_value', text='')
