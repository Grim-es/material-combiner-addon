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
import random
import pathlib
from .Packer import Packer

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from PIL import Image


class L(list):
    def __new__(self, *args, **kwargs):
        return super(L, self).__new__(self, args, kwargs)

    def __init__(self, *args, **kwargs):
        if len(args) == 1 and hasattr(args[0], '__iter__'):
            list.__init__(self, args[0])
        else:
            list.__init__(self, args)
        self.__dict__.update(kwargs)

    def __call__(self, **kwargs):
        self.__dict__.update(kwargs)
        return self


class GenMat(bpy.types.Operator):
    bl_idname = 'shotariya.gen_mat'
    bl_label = 'Combine materials'
    bl_description = 'Combine selected materials'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        start_time = time.time()
        files = []
        broken_materials = []
        copies = {}
        standard_mats = {}
        broken_links = []
        indexes = []
        scn = context.scene
        save_path = scn.combined_path
        unique_id = str(random.randrange(9999999999))
        if not save_path:
            self.report({'ERROR'}, 'Please select Folder for Combined Texture')
            return {'FINISHED'}
        bpy.ops.shotariya.uv_fixer()
        for obj in scn.objects:
            if obj.type == 'MESH':
                if not obj.data.uv_layers.active:
                    continue
                for mat_slot in obj.material_slots:
                    if mat_slot:
                        mat = mat_slot.material
                        mat_index = 0
                        for index in range(len(obj.material_slots)):
                            if obj.material_slots[index].material == mat:
                                mat_index = index
                        if mat.to_combine:
                            width = 0
                            height = 0
                            for face in obj.data.polygons:
                                if face.material_index == mat_index:
                                    face_coords = [obj.data.uv_layers.active.data[loop_idx].uv for loop_idx in
                                                   face.loop_indices]
                                    max_width = max([z.x for z in face_coords])
                                    max_height = max([z.y for z in face_coords])
                                    if max_width > width:
                                        width = max_width
                                    if max_height > height:
                                        height = max_height
                            if (width > 1) or (height > 1):
                                broken_materials.append(mat.name)
        if broken_materials:
            broken_materials = ',\n    '.join([', '.join(broken_materials[x:x + 5])
                                               for x in range(0, len(broken_materials), 5)])
            self.report({'ERROR'}, 'Following materials has UV bounds greater than 1:\n    {}\n\n'
                                   'Use these tools to fix:\n'
                                   '    • Save textures by UVs\n'
                                   '    • Pack UVs by splitting mesh\n'.format(broken_materials))
            return {'FINISHED'}
        for obj in scn.objects:
            if obj.type == 'MESH':
                if not obj.data.uv_layers.active:
                    continue
                for mat_slot in obj.material_slots:
                    if mat_slot:
                        mat = mat_slot.material
                        if mat.to_combine:
                            tex_slot = False
                            for j in range(len(mat.texture_slots)):
                                if mat.texture_slots[j]:
                                    if mat.texture_slots[j].texture:
                                        if mat.use_textures[j]:
                                            tex_slot = mat.texture_slots[j]
                                            break
                            if tex_slot:
                                tex = tex_slot.texture
                                if tex.image:
                                    image_path = bpy.path.abspath(tex.image.filepath)
                                    if len(image_path.split(os.sep)[-1].split('.')) > 1:
                                        if image_path not in files:
                                            files.append(image_path)
                                            standard_mats[mat] = image_path
                                        else:
                                            for s_mat, s_path in standard_mats.items():
                                                if s_path == image_path:
                                                    copies[s_mat] = mat
                            else:
                                diffuse = L(int(mat.diffuse_color.r * 255),
                                            int(mat.diffuse_color.g * 255),
                                            int(mat.diffuse_color.b * 255))
                                diffuse.size = (8, 8)
                                diffuse.name = mat.name
                                files.append(diffuse)
        for x in files:
            if not isinstance(x, (list,)):
                path = pathlib.Path(x)
                if not path.is_file():
                    broken_links.append(x.split(os.sep)[-1])
                    files.remove(x)
        combined_copies = 0
        if len(files) < 2:
            if copies:
                for obj in scn.objects:
                    if obj.type == 'MESH':
                        if not obj.data.uv_layers.active:
                            continue
                        for m_mat, c_mat in copies.items():
                            if m_mat.mat_index == c_mat.mat_index:
                                if (m_mat.name in obj.data.materials) and (c_mat.name in obj.data.materials):
                                    if m_mat.name != c_mat.name:
                                        combined_copies += 1
                                        to_delete = obj.data.materials.find(c_mat.name)
                                        for face in obj.data.polygons:
                                            if face.material_index == to_delete:
                                                face.material_index = obj.data.materials.find(m_mat.name)
                                        context.object.active_material_index = to_delete
                                        bpy.ops.object.material_slot_remove()
                if combined_copies > 0:
                    bpy.ops.shotariya.list_actions(action='GENERATE_MAT')
                    bpy.ops.shotariya.list_actions(action='GENERATE_TEX')
                    self.report({'INFO'}, 'Copies were combined')
                    return {'FINISHED'}
                else:
                    self.report({'ERROR'}, 'Nothing to Combine')
                    return {'FINISHED'}
            self.report({'ERROR'}, 'Nothing to Combine')
            return {'FINISHED'}
        images = sorted([{'w': i.size[0], 'h': i.size[1], 'path': path, 'img': i}
                         for path, i in ((x, Image.open(x).convert('RGBA')) if not isinstance(x, (list,))
                                         else (x.name, x) for x in files)],
                        key=lambda x: min([x['w'], x['h']]), reverse=True)
        packer = Packer.Packer(images)
        images = packer.fit()
        width = max([img['fit']['x'] + img['w'] for img in images])
        height = max([img['fit']['y'] + img['h'] for img in images])
        size = (width, height)
        if any(size) > 20000:
            self.report({'ERROR'}, 'Output Image Size way too big')
            return {'FINISHED'}
        image = Image.new('RGBA', size)
        for img in images:
            if img['fit']:
                if isinstance(img['img'], (list,)):
                    img['img'] = (img['img'][0], img['img'][1], img['img'][2])
                image.paste(img['img'], (img['fit']['x'],
                                         img['fit']['y'],
                                         img['fit']['x'] + img['w'],
                                         img['fit']['y'] + img['h']))
        for obj in scn.objects:
            if obj.type == 'MESH':
                if not obj.data.uv_layers.active:
                    continue
                scn.objects.active = obj
                mat_len = len(obj.material_slots)
                mats = []
                new_mats = []
                for mat_slot in obj.material_slots:
                    if mat_slot:
                        mat = mat_slot.material
                        if mat:
                            if mat.to_combine:
                                mat_name = 'combined_material_id{}_{}'.format(mat.mat_index, unique_id)
                                if mat_name not in obj.data.materials:
                                    if mat_name not in bpy.data.materials:
                                        material = bpy.data.materials.new(name=mat_name)
                                        indexes.append(mat.mat_index)
                                        tex_name = 'combined_texture_{}'.format(unique_id)
                                        if tex_name not in bpy.data.textures:
                                            texture = bpy.data.textures.new(tex_name, 'IMAGE')
                                        else:
                                            texture = bpy.data.textures[tex_name]
                                        slot = material.texture_slots.add()
                                        slot.texture = texture
                                    else:
                                        material = bpy.data.materials[mat_name]
                                    if material not in new_mats:
                                        new_mats.append(material)
                for materials in new_mats:
                    obj.data.materials.append(materials)
                for img in images:
                    for i in range(mat_len):
                        mat = obj.material_slots[i].material
                        mat_name = 'combined_material_id{}_{}'.format(mat.mat_index, unique_id)
                        tex_slot = False
                        for j in range(len(mat.texture_slots)):
                            if mat.texture_slots[j]:
                                if mat.texture_slots[j].texture:
                                    if mat.use_textures[j]:
                                        tex_slot = mat.texture_slots[j]
                                        break
                        if tex_slot:
                            tex = tex_slot.texture
                            texture_path = bpy.path.abspath(tex.image.filepath)
                            if texture_path == img['path']:
                                for face in obj.data.polygons:
                                    if face.material_index == i:
                                        face_coords = [obj.data.uv_layers.active.data[loop_idx].uv for loop_idx in
                                                       face.loop_indices]
                                        for z in face_coords:
                                            reset_x = z.x * (img['w'] - 2) / size[0]
                                            reset_y = 1 + z.y * (img['h'] - 2) / size[1] - img['h'] / size[1]
                                            z.x = reset_x + (img['fit']['x'] + 1) / size[0]
                                            z.y = reset_y - (img['fit']['y'] - 1) / size[1]
                                        face.material_index = obj.data.materials.find(mat_name)
                                if mat.name not in mats:
                                    mats.append(mat.name)
                        else:
                            if mat.to_combine:
                                if img['path'] == mat.name:
                                    for face in obj.data.polygons:
                                        if face.material_index == i:
                                            face_coords = [obj.data.uv_layers.active.data[loop_idx].uv for loop_idx in
                                                           face.loop_indices]
                                            for z in face_coords:
                                                reset_x = z.x * (img['w'] - 2) / size[0]
                                                reset_y = 1 + z.y * (img['h'] - 2) / size[1] - img['h'] / size[1]
                                                z.x = reset_x + (img['fit']['x'] + 1) / size[0]
                                                z.y = reset_y - (img['fit']['y'] - 1) / size[1]
                                            face.material_index = obj.data.materials.find(mat_name)
                                    if mat.name not in mats:
                                        mats.append(mat.name)
                for mater in mats:
                    context.object.active_material_index = [x.material.name for x in
                                                            context.object.material_slots].index(mater)
                    bpy.ops.object.material_slot_remove()
        image.save(os.path.join(save_path, 'combined_image_' + unique_id + '.png'))
        for index in indexes:
            mat = bpy.data.materials['combined_material_id{}_{}'.format(index, unique_id)]
            mat.mat_index = index
            mat.use_shadeless = True
            mat.alpha = 0
            mat.use_transparency = True
            mat.texture_slots[0].use_map_alpha = True
            tex = mat.texture_slots[0].texture
            tex.image = bpy.data.images.load(os.path.join(save_path, 'combined_image_' + unique_id + '.png'))
        for mesh in bpy.data.meshes:
            mesh.show_double_sided = True
        bpy.ops.shotariya.list_actions(action='GENERATE_MAT')
        bpy.ops.shotariya.list_actions(action='GENERATE_TEX')
        print('{} seconds passed'.format(time.time() - start_time))
        if broken_links:
            broken_links = ',\n    '.join([', '.join(broken_links[x:x + 5])
                                           for x in range(0, len(broken_links), 5)])
            self.report({'ERROR'}, 'Materials were combined\nFiles not found:\n    {}'.format(broken_links))
            return {'FINISHED'}
        self.report({'INFO'}, 'Materials were combined.')
        return{'FINISHED'}
