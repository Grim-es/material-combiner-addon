# MIT License

# Copyright (c) 2018 shotariya

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import bpy
import os
import sys
import time
import math

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from PIL import Image


class GenTex(bpy.types.Operator):
    bl_idname = 'shotariya.gen_tex'
    bl_label = 'Save Textures by UVs'
    bl_description = ''
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        start_time = time.time()
        scn = context.scene
        save_path = scn.tex_path
        if not save_path:
            self.report({'ERROR'}, 'Please select Folder for Combined Texture')
            return {'FINISHED'}
        bpy.ops.shotariya.uv_fixer()
        work = []
        for obj in context.scene.objects:
            if obj.type == 'MESH':
                if not obj.data.uv_layers.active or not obj.hide:
                    continue
                mat_len = len(obj.material_slots)
                mat_info = [[] for x in range(mat_len)]
                tex_info = [[] for x in range(mat_len)]
                for face in obj.data.polygons:
                    face_coords = [obj.data.uv_layers.active.data[loop_idx].uv for loop_idx in face.loop_indices]
                    mat_info[face.material_index].append(face_coords)
                for mat, faces in enumerate(mat_info):
                    x_list = [math.ceil(poly.x) for face in faces for poly in face if not math.isnan(poly.x)]
                    y_list = [math.ceil(poly.y) for face in faces for poly in face if not math.isnan(poly.y)]
                    tex_info[mat] = [max(x_list), max(y_list)]
                for index in range(mat_len):
                    mat = obj.material_slots[index].material
                    tex_slot = mat.texture_slots[0]
                    if tex_slot:
                        if (tex_info[index][0] > 1) or (tex_info[index][1] > 1):
                            tex = tex_slot.texture
                            if tex:
                                tex_info[index].append(bpy.path.abspath(tex.image.filepath))
                                tex_info[index].append(mat)
                        else:
                            tex = tex_slot.texture
                            if tex:
                                tex.to_save = False
                if len([True for info in tex_info if len(info) > 2]) != 0:
                    work.append(True)
                for info in tex_info:
                    if len(info) > 3:
                        img_name = info[2].split(os.sep)[-1].split('.')[0]
                        img = Image.open(info[2])
                        w, h = img.size
                        if info[0] == 0:
                            info[0] = 1
                        if info[1] == 0:
                            info[1] = 1
                        if info[0] > 64:
                            info[0] = 1
                        if info[1] > 64:
                            info[1] = 1
                        result = Image.new('RGBA', (w * info[0], h * info[1]))
                        for i in range(info[0]):
                            for j in range(info[1]):
                                x = i * w
                                y = j * h
                                result.paste(img, (x, y, x + w, y + h))
                        result.save(os.path.join(save_path, img_name + '_uv.png'), 'PNG')
                        mat = info[3]
                        mat_index = 0
                        for index in range(mat_len):
                            if obj.material_slots[index].material == mat:
                                mat_index = index
                        tex_slot = mat.texture_slots[0]
                        tex = tex_slot.texture
                        if tex.to_save:
                            tex.image = bpy.data.images.load(os.path.join(save_path, img_name + '_uv.png'))
                            for face in obj.data.polygons:
                                if face.material_index == mat_index:
                                    face_coords = [obj.data.uv_layers.active.data[loop_idx].uv for loop_idx in
                                                   face.loop_indices]
                                    for z in face_coords:
                                        z.x = z.x / info[0]
                                        z.y = z.y / info[1]
        if not work:
            self.report({'ERROR'}, 'All Selected texture UVs bounds are 0-1')
            return {'FINISHED'}
        bpy.ops.shotariya.list_actions(action='GENERATE_MAT')
        bpy.ops.shotariya.list_actions(action='GENERATE_TEX')
        print('{} seconds passed'.format(time.time() - start_time))
        self.report({'INFO'}, 'Textures were created.')
        return{'FINISHED'}
