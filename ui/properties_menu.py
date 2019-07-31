import bpy
from bpy.props import *
from .. import globs
from ..utils.images import get_image
from ..utils.materials import shader_type
from ..utils.textures import get_texture


class PropertiesMenu(bpy.types.Operator):
    bl_label = 'Settings for material:'
    bl_idname = 'smc.properties_menu'
    bl_description = 'Show settings for this material'
    bl_options = {'UNDO', 'INTERNAL'}

    list_id = IntProperty(default=0)

    def invoke(self, context, event):
        scn = context.scene
        dpi = bpy.context.preferences.system.dpi if globs.version else bpy.context.user_preferences.system.dpi
        wm = context.window_manager
        scn.smc_list_id = self.list_id
        return wm.invoke_props_dialog(self, width=dpi * 4)

    def check(self, context):
        return True

    def execute(self, context):
        return {'FINISHED'}

    def draw(self, context):
        scn = context.scene
        item = scn.smc_ob_data[scn.smc_list_id]
        if globs.version:
            img = None
            if item.mat.node_tree and item.mat.node_tree.nodes and 'mmd_base_tex' in item.mat.node_tree.nodes:
                img = item.mat.node_tree.nodes['mmd_base_tex'].image
        else:
            img = get_image(get_texture(item.mat))
        layout = self.layout
        col = layout.column()
        col.scale_y = 1.2
        col.prop(item.mat, 'name', text='', icon_value=item.mat.preview.icon_id)
        if img:
            col.label(text='Image size: {}x{}px'.format(img.size[0], img.size[1]))
            col.separator()
            col.prop(item.mat, 'smc_diffuse')
            if item.mat.smc_diffuse:
                if globs.version:
                    shader = shader_type(item.mat)
                    if shader == 'mmd':
                        col.prop(item.mat.node_tree.nodes['mmd_shader'].inputs['Diffuse Color'], 'default_value',
                                 text='')
                    elif shader == 'vrm':
                        col.prop(item.mat.node_tree.nodes['Group'].inputs[10], 'default_value', text='')
                else:
                    col.prop(item.mat, 'diffuse_color', text='')
                col.separator()
            col.prop(item.mat, 'smc_size')
            if item.mat.smc_size:
                col.prop(item.mat, 'smc_size_width')
                col.prop(item.mat, 'smc_size_height')
                col.separator()
        else:
            col.label(text='Image size: {0}x{0}px'.format(scn.smc_diffuse_size))
