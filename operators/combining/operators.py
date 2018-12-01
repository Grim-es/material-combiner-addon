import bpy
import os
import math
import random
try:
    from PIL import Image, ImageChops
except ImportError(Image, ImageChops):
    pass
from collections import defaultdict
from ... utils . materials import get_texture, get_diffuse
from ... utils . textures import tex_path


def get_materials_uv(scn):
    uv = defaultdict(list)
    for i in scn.smc_ob_data:
        if (i.type == 0) and i.used:
            for face in i.ob.data.polygons:
                face_uv = [i.ob.data.uv_layers.active.data[loop_idx].uv for loop_idx in face.loop_indices]
                min_x = min([math.floor(uv.x) for uv in face_uv if not math.isnan(uv.x)])
                min_y = min([math.floor(uv.y) for uv in face_uv if not math.isnan(uv.y)])
                for uvv in face_uv:
                    uvv.x -= min_x
                    uvv.y -= min_y
                if face.loop_indices:
                    for loop_idx in face.loop_indices:
                        mat = i.ob.data.materials[face.material_index]
                        uv[mat].append(i.ob.data.uv_layers.active.data[loop_idx].uv)
    return uv


def get_materials_data(scn, uv):
    data = []
    for i in scn.smc_ob_data:
        if (i.type == 1) and i.used and not any((x['mat'] == i.mat) or (i.mat in x['duplicates']) for x in data):
            if i.mat in uv:
                path = tex_path(get_texture(i.mat))
                diffuse = get_diffuse(i.mat)
                root_data = next((x for x in data if (x['path'] == path) and (x['diffuse'] == diffuse)), None)
                if root_data:
                    root_data['duplicates'].append(i.mat)
                    root_data['uv'] += uv[i.mat]
                else:
                    data.append({
                        'mat': i.mat,
                        'uv': uv[i.mat],
                        'path': path,
                        'diffuse': diffuse,
                        'duplicates': [],
                    })
            else:
                mat_idx = i.ob.data.materials.find(i.mat.name)
                i.ob.data.materials.pop(mat_idx, update_data=True)
    return data


def fill_uv(data):
    for i in data:
        i['uv_w'] = max(max([math.ceil(uv.x) for uv in i['uv'] if not math.isnan(uv.x)], default=1), 1)
        i['uv_h'] = max(max([math.ceil(uv.y) for uv in i['uv'] if not math.isnan(uv.y)], default=1), 1)
        if i['path']:
            i['img'] = Image.open(i['path']).convert('RGBA')
            if i['mat'].smc_size:
                i['img'].thumbnail(size=(i['mat'].smc_size_width, i['mat'].smc_size_height))
            if any((i['uv_w'], i['uv_h'])) > 0.999:
                uv_img = Image.new('RGBA', (i['img'].size[0] * i['uv_w'], i['img'].size[1] * i['uv_h']))
                for w in range(i['uv_w']):
                    for h in range(i['uv_h']):
                        uv_img.paste(i['img'], (
                            w * i['img'].size[0],
                            h * i['img'].size[1],
                            w * i['img'].size[0] + i['img'].size[0],
                            h * i['img'].size[1] + i['img'].size[1]
                        ))
                i['img'] = uv_img
            diffuse_img = Image.new('RGBA', (i['img'].size[0], i['img'].size[1]), i['diffuse'])
            i['img'] = ImageChops.multiply(i['img'], diffuse_img)
        else:
            i['img'] = Image.new('RGBA', (8, 8), i['diffuse'])
        i['w'] = i['img'].size[0]
        i['h'] = i['img'].size[1]
    return sorted(data, key=lambda x: min([x['w'], x['h']]), reverse=True)


def create_atlas(scn, data):
    size = (max([i['fit']['x'] + i['w'] for i in data]),
            max([i['fit']['y'] + i['h'] for i in data]))
    if scn.smc_size == 'PO2':
        size = (max(size),) * 2
    img = Image.new('RGBA', size)
    for i in data:
        if i['fit']:
            img.paste(i['img'], (
                i['fit']['x'],
                i['fit']['y'],
                i['fit']['x'] + i['w'],
                i['fit']['y'] + i['h']
            ))
    if scn.smc_size == 'CUST':
        img.thumbnail(size=(scn.smc_size_width, scn.smc_size_height))
    return img, size


def create_combined_mat(scn, img):
    unique_id = str(random.randrange(9999999999))
    path = os.path.join(os.path.dirname(bpy.data.filepath), 'combined_image_{}.png'.format(unique_id))
    scn.smc_save_path = path
    mat = bpy.data.materials.new(name='combined_material_{}'.format(unique_id))
    mat.texture_slots.add().texture = bpy.data.textures.new('combined_texture_{}'.format(unique_id), 'IMAGE')
    mat.use_shadeless = True
    mat.alpha = 0
    mat.use_transparency = True
    mat.diffuse_color = (1, 1, 1)
    mat.texture_slots[0].use_map_alpha = True
    img.save(str(path))
    mat.texture_slots[0].texture.image = bpy.data.images.load(path)
    return mat


def combine_uv(scn, data, size, mat):
    for i in scn.smc_ob_data:
        if (i.type == 0) and i.used:
            i.ob.data.materials.append(mat)
        if (i.type == 1) and i.used:
            i_data = next((x for x in data if (x['mat'] == i.mat) or (i.mat in x['duplicates'])), None)
            mat_idx = i.ob.data.materials.find(i.mat.name)
            for face in i.ob.data.polygons:
                if (face.material_index == mat_idx) and face.loop_indices:
                    for loop_idx in face.loop_indices:
                        uv = i.ob.data.uv_layers.active.data[loop_idx].uv
                        reset_x = uv.x / i_data['uv_w'] * (i_data['w'] - 2) / size[0]

                        reset_y = 1 + uv.y / i_data['uv_h'] * (i_data['h'] - 2) / size[1] - i_data['h'] / size[1]
                        uv.x = reset_x + (i_data['fit']['x'] + 1) / size[0]
                        uv.y = reset_y - (i_data['fit']['y'] - 1) / size[1]
                    face.material_index = i.ob.data.materials.find(mat.name)
            i.ob.data.materials.pop(mat_idx, update_data=True)


def combine_copies(scn, data):
    bpy.ops.smc.refresh_ob_data()
    for i in scn.smc_ob_data:
        if (i.type == 1) and i.used:
            if data[0]['mat'] != i.mat:
                mat_idx = i.ob.data.materials.find(i.mat.name)
                for face in i.ob.data.polygons:
                    if (face.material_index == mat_idx) and face.loop_indices:
                        face.material_index = i.ob.data.materials.find(data[0]['mat'].name)
                i.ob.data.materials.pop(mat_idx, update_data=True)
