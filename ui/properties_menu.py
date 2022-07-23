import bpy
from bpy.props import *
from .. import globs
from ..utils.material_source import MaterialSource
from ..utils.previews import get_preview
from ..utils.images import is_single_colour_generated


class PropertiesMenu(bpy.types.Operator):
    bl_label = 'Settings for material:'
    bl_idname = 'smc.properties_menu'
    bl_description = 'Show settings for this material'
    bl_options = {'UNDO', 'INTERNAL'}

    list_id = IntProperty(default=0)

    def invoke(self, context, event):
        scn = context.scene
        dpi = bpy.context.preferences.system.dpi if globs.is_blender_2_80_or_newer else bpy.context.user_preferences.system.dpi
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
        material_source = MaterialSource.from_material(item.mat)
        img = material_source.image
        layout = self.layout
        col = layout.column()
        col.scale_y = 1.2
        col.prop(item.mat, 'name', text='', icon_value=get_preview(item.mat).icon_id)
        if img:
            if is_single_colour_generated(img):
                col.label(text='Color size: {0}x{0}px (blank generated image)'.format(scn.smc_diffuse_size),
                          icon_value=get_preview(img).icon_id)
                col.prop(img, 'generated_color', text='')
                col.separator()
                col.prop(item.mat, 'smc_diffuse')
                if item.mat.smc_diffuse:
                    color_prop = material_source.color
                    if color_prop:
                        col.prop(color_prop.prop_holder, color_prop.path, text='')
                    else:
                        col.label(text="No diffuse color found")
            else:
                img_label_text = '{} size: {}x{}px'.format(img.name, img.size[0], img.size[1])
                col.label(text=img_label_text, icon_value=get_preview(img).icon_id)
                col.separator()
                col.prop(item.mat, 'smc_diffuse')
                if item.mat.smc_diffuse:
                    color_prop = material_source.color
                    if color_prop:
                        col.prop(color_prop.prop_holder, color_prop.path, text='')
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
            color_prop = material_source.color
            if color_prop:
                col.prop(color_prop.prop_holder, color_prop.path, text="Color (alpha ignored)")
            else:
                col.label(text="No diffuse color found, white will be used")
