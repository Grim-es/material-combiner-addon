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
import pathlib

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
        broken_links = []
        for obj in context.scene.objects:
            if obj.type == 'MESH':
                if not obj.data.uv_layers.active or obj.hide:
                    continue
                mat_len = len(obj.material_slots)
                mat_info = [[] for x in range(mat_len)]
                for face in obj.data.polygons:
                    face_coords = [obj.data.uv_layers.active.data[loop_idx].uv for loop_idx in face.loop_indices]
                    mat_info[face.material_index].append(face_coords)
                for index, faces in enumerate(mat_info):
                    x_list = [math.ceil(poly.x) for face in faces for poly in face if not math.isnan(poly.x)]
                    y_list = [math.ceil(poly.y) for face in faces for poly in face if not math.isnan(poly.y)]
                    mat = obj.material_slots[index].material
                    if mat.to_tex:
                        tex_slot = False
                        for j in range(len(mat.texture_slots)):
                            if mat.texture_slots[j]:
                                if mat.texture_slots[j].texture:
                                    if mat.use_textures[j]:
                                        tex_slot = mat.texture_slots[j]
                                        break
                        if tex_slot:
                            if (max(x_list) > 1) or (max(y_list) > 1):
                                tex = tex_slot.texture
                                if tex:
                                    img_name = bpy.path.abspath(tex.image.filepath).split(os.sep)[-1].split('.')[0]
                                    check_for_file = pathlib.Path(bpy.path.abspath(tex.image.filepath))
                                    if not check_for_file.is_file():
                                        broken_links.append(img_name)
                                        continue
                                    img = Image.open(bpy.path.abspath(tex.image.filepath))
                                    w, h = img.size
                                    max_x = max(x_list)
                                    max_y = max(y_list)
                                    if max_x == 0:
                                        max_x = 1
                                    if max_y == 0:
                                        max_y = 1
                                    if max_x > 64:
                                        max_x = 1
                                    if max_y > 64:
                                        max_y = 1
                                    result = Image.new('RGBA', (w * max_x, h * max_y))
                                    print(result.size)
                                    for i in range(max_x):
                                        for j in range(max_y):
                                            x = i * w
                                            y = j * h
                                            result.paste(img, (x, y, x + w, y + h))
                                    result.save(os.path.join(save_path, img_name + '_uv.png'), 'PNG')
                                    tex = bpy.data.textures.new(img_name + '_uv', 'IMAGE')
                                    tex.image = bpy.data.images.load(os.path.join(save_path, img_name + '_uv.png'))
                                    tex_slot.texture = tex
                                    for face in obj.data.polygons:
                                        if face.material_index == index:
                                            face_coords = [obj.data.uv_layers.active.data[loop_idx].uv for loop_idx in
                                                           face.loop_indices]
                                            for z in face_coords:
                                                z.x = z.x / max_x
                                                z.y = z.y / max_y
                                work.append(True)
        print(broken_links)
        if not work:
            self.report({'ERROR'}, 'All Selected texture UVs bounds are 0-1')
            return {'FINISHED'}
        bpy.ops.shotariya.list_actions(action='GENERATE_MAT')
        bpy.ops.shotariya.list_actions(action='GENERATE_TEX')
        if broken_links:
            broken_links = ',\n    '.join([', '.join(broken_links[x:x + 5])
                                           for x in range(0, len(broken_links), 5)])
            self.report({'ERROR'}, 'Textures were combined\nFiles not found:\n    {}'.format(broken_links))
            return {'FINISHED'}
        print('{} seconds passed'.format(time.time() - start_time))
        self.report({'INFO'}, 'Textures were created.')
        return{'FINISHED'}
