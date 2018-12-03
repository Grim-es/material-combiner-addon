import bpy
import os
from bpy.props import *


class ImgTexItemAdd(bpy.types.Operator):
    bl_idname = 'smc.img_add'
    bl_label = 'Add Item'

    def execute(self, context):
        img_name = context.scene.smc_image_preview
        img = bpy.data.images[img_name]
        item = img.smc_img_list.add()
        item.img_name = 'Empty'
        item.img_path = ''
        item.img_type = 0
        img.smc_img_list_id = len(img.smc_img_list) - 1
        return {'FINISHED'}


class ImgTexItemRemove(bpy.types.Operator):
    bl_idname = 'smc.img_remove'
    bl_label = 'Remove Item'

    def execute(self, context):
        img_name = context.scene.smc_image_preview
        img = bpy.data.images[img_name]
        if len(img.smc_img_list) > 0:
            img.smc_img_list.remove(img.smc_img_list_id)
        if img.smc_img_list_id > (len(img.smc_img_list) - 1):
            img.smc_img_list_id = img.smc_img_list_id - 1
        return {'FINISHED'}


class ImgTexItemMove(bpy.types.Operator):
    bl_idname = 'smc.img_move'
    bl_label = "Move Item"

    type = bpy.props.StringProperty(default='UP')

    def execute(self, context):
        img_name = context.scene.smc_image_preview
        img = bpy.data.images[img_name]
        if self.type == 'UP':
            img.smc_img_list.move(img.smc_img_list_id, img.smc_img_list_id - 1)
            if (img.smc_img_list_id - 1) >= 0:
                img.smc_img_list_id = img.smc_img_list_id - 1
        elif self.type == 'DOWN':
            img.smc_img_list.move(img.smc_img_list_id, img.smc_img_list_id + 1)
            if (img.smc_img_list_id + 1) != len(img.smc_img_list):
                img.smc_img_list_id = img.smc_img_list_id + 1
        return {'FINISHED'}


class ImgTexItemReset(bpy.types.Operator):
    bl_idname = 'smc.img_reset'
    bl_label = 'Reset Item'
    bl_description = 'Reset Selected Texture'
    bl_options = {'UNDO', 'INTERNAL'}

    list_id = IntProperty(default=0)

    def execute(self, context):
        img_name = context.scene.smc_image_preview
        img = bpy.data.images[img_name]
        img.smc_img_list[self.list_id].img_name = 'Empty'
        img.smc_img_list[self.list_id].img_path = ''
        img.smc_img_list[self.list_id].img_type = 0
        return {'FINISHED'}		


class ImgTexItemColor(bpy.types.Operator):
    bl_idname = 'smc.img_color'
    bl_label = 'Diffuse Item'
    bl_description = 'Texture as Color'
    bl_options = {'UNDO', 'INTERNAL'}

    list_id = IntProperty(default=0)

    def execute(self, context):
        img_name = context.scene.smc_image_preview
        img = bpy.data.images[img_name]
        img.smc_img_list[self.list_id].img_name = 'Color'
        img.smc_img_list[self.list_id].img_alpha_color = (1.0, 1.0, 1.0, 1.0)
        img.smc_img_list[self.list_id].img_path = ''
        img.smc_img_list[self.list_id].img_type = 2
        return {'FINISHED'}


class ImgTexItemPath(bpy.types.Operator):
    bl_idname = 'smc.img_path'
    bl_label = 'Path Item'
    bl_description = 'Select an Image'
    bl_options = {'UNDO', 'INTERNAL'}

    list_id = IntProperty(default=0)
    filepath = StringProperty(name='Select an Image', maxlen=1024, options={'HIDDEN'})
    filename = StringProperty(name='Image Name', default='', options={'HIDDEN'})
    directory = StringProperty(maxlen=1024, default='', subtype='FILE_PATH', options={'HIDDEN'})
    filter_glob = StringProperty(
        default='*.BMP;*.GIF;*.JPEG;*.JPG;*.PNG;*.TIFF;*.TIF;*.DDS;*.PSD;*.TGA',
        options={'HIDDEN'}
    )

    def execute(self, context):
        img_name = context.scene.smc_image_preview
        img = bpy.data.images[img_name]
        name = self.filename
        path = os.path.join(self.directory, self.filename)
        img.smc_img_list[self.list_id].img_name = name.split('.')[0]
        img.smc_img_list[self.list_id].img_path = path
        img.smc_img_list[self.list_id].img_color = (1.0, 1.0, 1.0)
        img.smc_img_list[self.list_id].img_type = 1
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
