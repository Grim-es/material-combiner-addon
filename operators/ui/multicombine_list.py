import os

import bpy
from bpy.props import *


class MultiCombineImageAdd(bpy.types.Operator):
    bl_idname = 'smc.img_add'
    bl_label = 'Add Item'

    def execute(self, context):
        scn = context.scene
        item = scn.smc_ob_data[scn.smc_list_id]
        m_item = item.mat.smc_multi_list.add()
        m_item.img_name = 'Empty'
        m_item.img_path = ''
        m_item.img_type = 0
        item.mat.smc_multi_list_id = len(item.mat.smc_multi_list) - 1
        return {'FINISHED'}


class MultiCombineImageRemove(bpy.types.Operator):
    bl_idname = 'smc.img_remove'
    bl_label = 'Remove Item'

    def execute(self, context):
        scn = context.scene
        item = scn.smc_ob_data[scn.smc_list_id]
        if len(item.mat.smc_multi_list) > 0:
            item.mat.smc_multi_list.remove(item.mat.smc_multi_list_id)
        if item.mat.smc_multi_list_id > (len(item.mat.smc_multi_list) - 1):
            item.mat.smc_multi_list_id = item.mat.smc_multi_list_id - 1
        return {'FINISHED'}


class MultiCombineImageMove(bpy.types.Operator):
    bl_idname = 'smc.img_move'
    bl_label = "Move Item"

    type = bpy.props.StringProperty(default='UP')

    def execute(self, context):
        scn = context.scene
        item = scn.smc_ob_data[scn.smc_list_id]
        if self.type == 'UP':
            item.mat.smc_multi_list.move(item.mat.smc_multi_list_id, item.mat.smc_multi_list_id - 1)
            if (item.mat.smc_multi_list_id - 1) >= 0:
                item.mat.smc_multi_list_id = item.mat.smc_multi_list_id - 1
        elif self.type == 'DOWN':
            item.mat.smc_multi_list.move(item.mat.smc_multi_list_id, item.mat.smc_multi_list_id + 1)
            if (item.mat.smc_multi_list_id + 1) != len(item.mat.smc_multi_list):
                item.mat.smc_multi_list_id = item.mat.smc_multi_list_id + 1
        return {'FINISHED'}


class MultiCombineImageReset(bpy.types.Operator):
    bl_idname = 'smc.img_reset'
    bl_label = 'Reset Item'
    bl_description = 'Reset Selected Texture'
    bl_options = {'UNDO', 'INTERNAL'}

    list_id = IntProperty(default=0)

    def execute(self, context):
        scn = context.scene
        item = scn.smc_ob_data[scn.smc_list_id]
        item.mat.smc_multi_list[self.list_id].img_name = 'Empty'
        item.mat.smc_multi_list[self.list_id].img_path = ''
        item.mat.smc_multi_list[self.list_id].img_type = 0
        return {'FINISHED'}


class MultiCombineColor(bpy.types.Operator):
    bl_idname = 'smc.img_color'
    bl_label = 'Diffuse Item'
    bl_description = 'Texture as Color'
    bl_options = {'UNDO', 'INTERNAL'}

    list_id = IntProperty(default=0)

    def execute(self, context):
        scn = context.scene
        item = scn.smc_ob_data[scn.smc_list_id]
        item.mat.smc_multi_list[self.list_id].img_name = 'Color'
        item.mat.smc_multi_list[self.list_id].img_alpha_color = (1.0, 1.0, 1.0, 1.0)
        item.mat.smc_multi_list[self.list_id].img_path = ''
        item.mat.smc_multi_list[self.list_id].img_type = 2
        return {'FINISHED'}


class MultiCombineImagePath(bpy.types.Operator):
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
        scn = context.scene
        item = scn.smc_ob_data[scn.smc_list_id]
        name = self.filename
        path = os.path.join(self.directory, self.filename)
        item.mat.smc_multi_list[self.list_id].img_name = name.split('.')[0]
        item.mat.smc_multi_list[self.list_id].img_path = path
        item.mat.smc_multi_list[self.list_id].img_color = (1.0, 1.0, 1.0)
        item.mat.smc_multi_list[self.list_id].img_type = 1
        bpy.ops.smc.properties_menu('INVOKE_DEFAULT', list_id=scn.smc_list_id)
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
