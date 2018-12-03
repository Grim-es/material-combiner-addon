import bpy
import os
from time import time
from bpy.props import *
from . operators import get_materials_uv, get_materials_data, fill_uv, create_atlas
from . operators import create_multi_atlas, create_combined_mat, combine_uv, combine_copies
from . packing import BinPacker


class SavePath(bpy.types.Operator):
    bl_idname = 'smc.save_path'
    bl_label = 'Select a Folder for Combined Image'
    bl_description = 'Select a path for combined image'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    filepath = StringProperty(subtype='DIR_PATH')
    filter_glob = StringProperty(default='', options={'HIDDEN'})

    def execute(self, context):
        scn = context.scene
        scn.smc_save_path = self.filepath.rstrip(os.sep).lower()
        return {'FINISHED'}

    def invoke(self, context, event):
        scn = context.scene
        self.filepath = scn.smc_save_path + os.sep
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class Combiner(bpy.types.Operator):
    bl_idname = 'smc.combiner'
    bl_label = 'Combine'
    bl_description = 'Combine materials'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        start_time = time()
        scn = context.scene
        cur_time = time()
        uv = get_materials_uv(scn)
        print('get_materials: {}'.format(time() - cur_time))
        cur_time = time()
        data = get_materials_data(scn, uv)
        print('get_materials_data: {}'.format(time() - cur_time))
        if (len(data) == 1) and data[0]['duplicates']:
            combine_copies(scn, data)
            bpy.ops.smc.refresh_ob_data()
            self.report({'INFO'}, 'Copies were combined')
            return {'FINISHED'}
        elif not data or (len(data) == 1):
            self.report({'ERROR'}, 'Nothing to Combine')
            return {'FINISHED'}
        cur_time = time()
        data = BinPacker(fill_uv(data)).fit()
        print('data_bin: {}'.format(time() - cur_time))
        cur_time = time()
        img, size = create_atlas(scn, data)
        print('create_atlas: {}'.format(time() - cur_time))
        if scn.smc_multi:
            cur_time = time()
            img += create_multi_atlas(scn, data, size)
            print('create_multi_atlas: {}'.format(time() - cur_time))
        cur_time = time()
        mat, unique_id = create_combined_mat(scn, img)
        print('comb_mat: {}'.format(time() - cur_time))
        cur_time = time()
        combine_uv(scn, data, size, mat)
        print('combine_uv: {}'.format(time() - cur_time))
        if os.name == 'nt' and scn.smc_compress:
            cur_time = time()
            for idx in range(len(img)):
                bpy.ops.smc.compress(file='combined_image_{}_{}.png'.format(idx, unique_id))
            print('Compression: {}'.format(time() - cur_time))
        bpy.ops.smc.refresh_ob_data()
        print('{} seconds passed'.format(time() - start_time))
        self.report({'INFO'}, 'Materials were combined.')
        return {'FINISHED'}
