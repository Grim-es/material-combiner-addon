import math
import os
import random
from collections import OrderedDict
from collections import defaultdict

import bpy

try:
    from PIL import Image
    from PIL import ImageChops
except ImportError:
    Image = None
    ImageChops = None
from ... import globs
from ...utils.objects import get_obs
from ...utils.objects import get_polys
from ...utils.objects import get_uv
from ...utils.objects import align_uv
from ...utils.materials import shader_type
from ...utils.materials import get_diffuse
from ...utils.materials import sort_materials
from ...utils.textures import get_texture
from ...utils.images import get_image
from ...utils.images import get_image_path

if Image:
    Image.MAX_IMAGE_PIXELS = None


def set_ob_mode(scn):
    obs = get_obs(scn.objects)
    for ob in obs:
        scn.objects.active = ob
        bpy.ops.object.mode_set(mode='OBJECT')


def get_data(data):
    mats = defaultdict(dict)
    for i in data:
        if i.type == 1 and i.used:
            mats[i.ob.name][i.mat] = i.layer
    return mats


def get_mats_uv(scn, ob_mats):
    mats_uv = {}
    for ob_n, i in ob_mats.items():
        ob = scn.objects[ob_n]
        mats_uv[ob_n] = defaultdict(list)
        for idx, polys in get_polys(ob).items():
            if ob.data.materials[idx] in i.keys():
                for poly in polys:
                    mats_uv[ob_n][ob.data.materials[idx]].extend(align_uv(get_uv(ob, poly)))
    return mats_uv


def clear_empty_mats(scn, data, mats_uv):
    for ob_n, i in data.items():
        ob = scn.objects[ob_n]
        for mat in i.keys():
            if mat not in mats_uv[ob_n].keys():
                mat_idx = ob.data.materials.find(mat.name)
                if globs.version > 1:
                    ob.data.materials.pop(index=mat_idx)
                else:
                    ob.data.materials.pop(index=mat_idx, update_data=True)


def get_duplicates(mats_uv):
    mat_list = list(set([mat for mats in mats_uv.values() for mat in mats.keys()]))
    mat_dict = sort_materials(mat_list)
    for mats in mat_dict.values():
        for mat in mats[1:]:
            mat.root_mat = mats[0]


def get_structure(scn, data, mats_uv):
    structure = {}
    for ob_n, i in data.items():
        ob = scn.objects[ob_n]
        for mat in i.keys():
            if mat.name in ob.data.materials:
                root_mat = mat.root_mat if mat.root_mat else mat
                if root_mat not in structure:
                    structure[root_mat] = {
                        'gfx': {
                            'img': None,
                            'size': (),
                            'uv_size': ()
                        },
                        'dup': [],
                        'ob': [],
                        'uv': []
                    }
                if mat.root_mat and mat not in structure[root_mat]['dup']:
                    structure[root_mat]['dup'].append(mat.name)
                if ob not in structure[root_mat]['ob']:
                    structure[root_mat]['ob'].append(ob.name)
                structure[root_mat]['uv'].extend(mats_uv[ob_n][mat])
    return structure


def clear_duplicates(scn, data):
    for i in data.values():
        for ob_n in i['ob']:
            ob = scn.objects[ob_n]
            for dup_n in i['dup']:
                delete_material(ob, dup_n)


def delete_material(mesh, mat_name):
    mat_idx = get_material_index(mesh, mat_name)
    if mat_idx:
        if globs.version > 1:
            mesh.data.materials.pop(index=mat_idx)
        else:
            mesh.data.materials.pop(index=mat_idx, update_data=True)


def get_material_index(mesh, mat_name):
    for i, mat in enumerate(mesh.data.materials):
        if mat.name == mat_name:
            return i


def get_size(scn, data):
    for mat, i in data.items():
        if globs.version > 0:
            img = None
            shader = shader_type(mat) if mat else None
            if shader == 'mmd':
                img = mat.node_tree.nodes['mmd_base_tex'].image
            elif shader == 'vrm' or shader == 'xnalara' or shader == 'diffuse' or shader == 'emission':
                img = mat.node_tree.nodes['Image Texture'].image
        else:
            img = get_image(get_texture(mat))
        path = get_image_path(img)
        max_x = max(max([uv.x for uv in i['uv'] if not math.isnan(uv.x)], default=1), 1)
        max_y = max(max([uv.y for uv in i['uv'] if not math.isnan(uv.y)], default=1), 1)
        i['gfx']['uv_size'] = (max_x if max_x < 25 else 1, max_y if max_y < 25 else 1)
        if not scn.smc_crop:
            i['gfx']['uv_size'] = tuple(map(math.ceil, i['gfx']['uv_size']))
        if path:
            if mat.smc_size:
                img_size = (min(mat.smc_size_width, img.size[0]),
                            min(mat.smc_size_height, img.size[1]))
            else:
                img_size = (img.size[0], img.size[1])
            i['gfx']['size'] = tuple(
                int(s * uv_s + int(scn.smc_gaps)) for s, uv_s in zip(img_size, i['gfx']['uv_size']))
        else:
            i['gfx']['size'] = (scn.smc_diffuse_size + int(scn.smc_gaps),) * 2
    return OrderedDict(sorted(data.items(), key=lambda x: min(x[1]['gfx']['size']), reverse=True))


def get_uv_image(item, img, size):
    uv_img = Image.new('RGBA', size)
    for w in range(math.ceil(item['gfx']['uv_size'][0])):
        for h in range(math.ceil(item['gfx']['uv_size'][1])):
            uv_img.paste(img, (
                w * img.size[0],
                uv_img.size[1] - img.size[1] - h * img.size[1],
                w * img.size[0] + img.size[0],
                uv_img.size[1] - img.size[1] - h * img.size[1] + img.size[1]
            ))
    return uv_img


def get_gfx(scn, mat, item, src):
    size = tuple(size - int(scn.smc_gaps) for size in item['gfx']['size'])
    if isinstance(src, str):
        if src:
            img = Image.open(src).convert('RGBA')
            if img.size != size:
                img.resize(size, Image.ANTIALIAS)
            if mat.smc_size:
                img.thumbnail((mat.smc_size_width, mat.smc_size_height), Image.ANTIALIAS)
            if any(item['gfx']['uv_size']) > 0.999:
                img = get_uv_image(item, img, size)
            if mat.smc_diffuse:
                diffuse_img = Image.new('RGBA', size, get_diffuse(mat))
                img = ImageChops.multiply(img, diffuse_img)
        else:
            img = Image.new('RGBA', size, get_diffuse(mat))
    else:
        img = Image.new('RGBA', size, src)
    return img


def get_atlas(scn, data, size):
    if scn.smc_size == 'PO2':
        size = tuple(1 << (x - 1).bit_length() for x in size)
    elif scn.smc_size == 'QUAD':
        size = (max(size),) * 2
    for mat, item in data.items():
        if globs.version > 0:
            item['gfx']['img'] = ''
            shader = shader_type(mat) if mat else None
            if shader == 'mmd':
                item['gfx']['img'] = get_image_path(mat.node_tree.nodes['mmd_base_tex'].image)
            elif shader == 'vrm' or shader == 'xnalara' or shader == 'diffuse' or shader == 'emission':
                item['gfx']['img'] = get_image_path(mat.node_tree.nodes['Image Texture'].image)
        else:
            item['gfx']['img'] = get_image_path(get_image(get_texture(mat)))
    img = Image.new('RGBA', size)
    for mat, i in data.items():
        if i['gfx']['fit']:
            if i['gfx']['img'] is not None:
                img.paste(get_gfx(scn, mat, i, i['gfx']['img']), (i['gfx']['fit']['x'] + int(scn.smc_gaps / 2),
                                                                  i['gfx']['fit']['y'] + int(scn.smc_gaps / 2)))
    if scn.smc_size == 'CUST':
        img.thumbnail((scn.smc_size_width, scn.smc_size_height), Image.ANTIALIAS)
    return img


def get_aligned_uv(scn, data, size):
    for mat, i in data.items():
        w, h = i['gfx']['size']
        uv_w, uv_h = i['gfx']['uv_size']
        for uv in i['uv']:
            reset_x = uv.x / uv_w * (w - 2 - int(scn.smc_gaps)) / size[0]
            reset_y = 1 + uv.y / uv_h * (h - 2 - int(scn.smc_gaps)) / size[1] - h / size[1]
            uv.x = reset_x + (i['gfx']['fit']['x'] + 1 + int(scn.smc_gaps / 2)) / size[0]
            uv.y = reset_y - (i['gfx']['fit']['y'] - 1 - int(scn.smc_gaps / 2)) / size[1]


def get_comb_mats(scn, atlas, mats_uv):
    layers = set(i.layer for i in scn.smc_ob_data if (i.type == 1) and i.used and (i.mat in mats_uv[i.ob.name].keys()))
    existed_ids = [int(i.mat.name.split('_')[-2]) for i in scn.smc_ob_data if (i.type == 1) and
                   i.mat.name.startswith('material_atlas_')]
    unique_id = random.choice([i for i in range(10000, 99999) if i not in existed_ids])
    path = os.path.join(scn.smc_save_path, 'Atlas_{0}.png'.format(unique_id))
    atlas.save(path)
    texture = bpy.data.textures.new('texture_atlas_{0}'.format(unique_id), 'IMAGE')
    image = bpy.data.images.load(path)
    texture.image = image
    mats = {}
    for idx in layers:
        mat = bpy.data.materials.new(name='material_atlas_{0}_{1}'.format(unique_id, idx))
        if globs.version > 0:
            mat.blend_method = 'CLIP'
            mat.use_backface_culling = True
            mat.use_nodes = True
            node_texture = mat.node_tree.nodes.new(type='ShaderNodeTexImage')
            node_texture.image = image
            node_texture.label = 'Material Combiner Texture'
            node_texture.location = -300, 300
            mat.node_tree.links.new(node_texture.outputs['Color'],
                                    mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
            mat.node_tree.links.new(node_texture.outputs['Alpha'],
                                    mat.node_tree.nodes['Principled BSDF'].inputs['Alpha'])
        else:
            mat.use_shadeless = True
            mat.alpha = 0
            mat.use_transparency = True
            mat.diffuse_color = (1, 1, 1)
            tex = mat.texture_slots.add()
            tex.texture = texture
            tex.use_map_alpha = True
        mats[idx] = mat
    return mats


def assign_comb_mats(scn, ob_mats, mats_uv, atlas):
    comb_mats = get_comb_mats(scn, atlas, mats_uv)
    for ob_n, i in ob_mats.items():
        ob = scn.objects[ob_n]
        for idx in set(i.values()):
            if idx in comb_mats.keys():
                ob.data.materials.append(comb_mats[idx])
        for idx, polys in get_polys(ob).items():
            if ob.data.materials[idx] in i.keys():
                mat_idx = ob.data.materials.find(comb_mats[i[ob.data.materials[idx]]].name)
                for poly in polys:
                    poly.material_index = mat_idx


def clear_mats(scn, mats_uv):
    for ob_n, i in mats_uv.items():
        ob = scn.objects[ob_n]
        for mat in i.keys():
            mat_idx = ob.data.materials.find(mat.name)
            if globs.version > 1:
                ob.data.materials.pop(index=mat_idx)
            else:
                ob.data.materials.pop(index=mat_idx, update_data=True)
