import bpy
from bpy.props import *
from .. import globs
from ..utils.materials import get_diffuse, get_material_image
from ..utils.textures import get_texture, get_image


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
        img = get_material_image(item.mat)
        layout = self.layout
        col = layout.column()
        col.scale_y = 1.2
        col.prop(item.mat, 'name', text='', icon_value=item.mat.preview.icon_id)
        if img:
            img_label_text = '{} size: {}x{}px'.format(img.name, img.size[0], img.size[1])
            if img.preview:
                col.label(text=img_label_text, icon_value=img.preview.icon_id)
            else:
                col.label(text=img_label_text, icon='QUESTION')
            col.separator()
            col.prop(item.mat, 'smc_diffuse')
            if item.mat.smc_diffuse:
                data, prop = get_diffuse(item.mat, ui=True)
                if data and prop:
                    col.prop(data, prop, text='')
                else:
                    col.label(text="No diffuse color found")
                col.separator()
            col.prop(item.mat, 'smc_size')
            if item.mat.smc_size:
                col.prop(item.mat, 'smc_size_width')
                col.prop(item.mat, 'smc_size_height')
                col.separator()
        else:
            col.label(text='Color size: {0}x{0}px (no image found)'.format(scn.smc_diffuse_size))
            col.separator()
            data, prop = get_diffuse(item.mat, ui=True)
            if data and prop:
                col.prop(data, prop, text="Color")
            else:
                col.label(text="No diffuse color found, white will be used")
