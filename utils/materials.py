import math
from collections import defaultdict

import bpy
from .images import get_image
from .images import get_image_path
from .textures import get_texture
from .. import globs


def get_materials(ob):
    return [mat_slot.material for mat_slot in ob.material_slots]


def shader_type(mat):
    if mat.node_tree and mat.node_tree.nodes and 'mmd_base_tex' in mat.node_tree.nodes:
        return 'mmd'
    elif (mat.node_tree and mat.node_tree.nodes and 'Group' in mat.node_tree.nodes and 'Image Texture' in
          mat.node_tree.nodes and mat.node_tree.nodes['Group'].node_tree.name == 'MToon_unversioned'):
        return 'vrm'
    elif (mat.node_tree and mat.node_tree.nodes and 'Principled BSDF' in mat.node_tree.nodes and
          'Image Texture' in mat.node_tree.nodes):
        return 'xnalara'


def sort_materials(mat_list):
    for mat in bpy.data.materials:
        mat.root_mat = None
    mat_dict = defaultdict(list)
    for mat in mat_list:
        if globs.version:
            path = None
            shader = shader_type(mat)
            if shader == 'mmd':
                path = get_image_path(mat.node_tree.nodes['mmd_base_tex'].image)
            elif (shader == 'vrm') or (shader == 'xnalara'):
                path = get_image_path(mat.node_tree.nodes['Image Texture'].image)
        else:
            path = get_image_path(get_image(get_texture(mat)))
        if path:
            mat_dict[(path, get_diffuse(mat) if mat.smc_diffuse else None)].append(mat)
        else:
            mat_dict[get_diffuse(mat)].append(mat)
    return mat_dict


def rgb_to_255_scale(diffuse):
    rgb = []
    for c in diffuse:
        if c < 0.0031308:
            srgb = 0.0 if c < 0.0 else c * 12.92
        else:
            srgb = 1.055 * math.pow(c, 1.0 / 2.4) - 0.055
        rgb.append(max(min(int(srgb * 255 + 0.5), 255), 0))
    return tuple(rgb)


def get_diffuse(mat):
    if globs.version:
        shader = shader_type(mat)
        if shader == 'mmd':
            return rgb_to_255_scale(mat.node_tree.nodes['mmd_shader'].inputs['Diffuse Color'].default_value[:])
        elif shader == 'vrm':
            return rgb_to_255_scale(mat.node_tree.nodes['Group'].inputs[10].default_value[:])
        return tuple((255, 255, 255))
    else:
        return rgb_to_255_scale(mat.diffuse_color)
