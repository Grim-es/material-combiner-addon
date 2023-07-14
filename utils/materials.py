from collections import defaultdict
from typing import Set
from typing import Tuple
from typing import Union
from typing import ValuesView

import bpy
import numpy as np

from .images import get_image
from .images import get_image_path
from .textures import get_texture
from .. import globs
from ..type_annotations import Diffuse
from ..type_annotations import MatDict


def get_materials(ob: bpy.types.Object) -> Set[bpy.types.Material]:
    return {mat_slot.material for mat_slot in ob.material_slots}


def shader_type(mat: bpy.types.Material) -> Union[str, None]:
    if not (mat.node_tree and mat.node_tree.nodes):
        return

    if 'mmd_shader' in mat.node_tree.nodes and 'mmd_base_tex' in mat.node_tree.nodes:
        return 'mmd'
    elif 'mmd_shader' in mat.node_tree.nodes:
        return 'mmdCol'

    elif ('Group' in mat.node_tree.nodes and 'Image Texture' in mat.node_tree.nodes and mat.node_tree.nodes[
        'Group'].node_tree.name == 'MToon_unversioned'):
        return 'vrm'
    elif ('Group' in mat.node_tree.nodes and
          mat.node_tree.nodes['Group'].node_tree.name == 'MToon_unversioned'):
        return 'vrmCol'

    elif ('Group' in mat.node_tree.nodes and mat.node_tree.nodes[
        'Group'].node_tree.name == 'XPS Shader' and 'Image Texture' in mat.node_tree.nodes):
        return 'xnalara'
    elif 'Group' in mat.node_tree.nodes and mat.node_tree.nodes['Group'].node_tree.name == 'Group':
        return 'xnalaraNewCol'

    elif 'Principled BSDF' in mat.node_tree.nodes and 'Image Texture' in mat.node_tree.nodes:
        return 'xnalara'
    elif 'Principled BSDF' in mat.node_tree.nodes:
        return 'xnalaraCol'

    elif 'Diffuse BSDF' in mat.node_tree.nodes and 'Image Texture' in mat.node_tree.nodes:
        return 'diffuse'
    elif 'Diffuse BSDF' in mat.node_tree.nodes:
        return 'diffuseCol'

    elif 'Emission' in mat.node_tree.nodes and 'Image Texture' in mat.node_tree.nodes:
        return 'emission'
    elif 'Emission' in mat.node_tree.nodes:
        return 'emissionCol'


def sort_materials(mat_list: Set[bpy.types.Material]) -> ValuesView[MatDict]:
    for mat in bpy.data.materials:
        mat.root_mat = None

    mat_dict = MatDict(defaultdict(list))

    for mat in mat_list:
        if globs.is_blender_2_80_or_newer:
            path = None
            shader = shader_type(mat) if mat else False
            if shader == 'mmd':
                path = get_image_path(mat.node_tree.nodes['mmd_base_tex'].image)
            elif shader in ['vrm', 'xnalara', 'diffuse', 'emission']:
                path = get_image_path(mat.node_tree.nodes['Image Texture'].image)
        else:
            path = get_image_path(get_image(get_texture(mat)))

        if path:
            mat_dict[(path, get_diffuse(mat) if mat.smc_diffuse else None)].append(mat)
        else:
            mat_dict[get_diffuse(mat)].append(mat)

    return mat_dict.values()


def rgb_to_255_scale(diffuse: Diffuse) -> Tuple[int, int, int]:
    rgb = np.empty(shape=(0,), dtype=int)
    for c in diffuse:
        if c < 0.0:
            srgb = 0
        elif c < 0.0031308:
            srgb = c * 12.92
        else:
            srgb = 1.055 * pow(c, 1.0 / 2.4) - 0.055
        rgb = np.append(rgb, np.clip(round(srgb * 255), 0, 255))
    return tuple(rgb)


def get_diffuse(mat: bpy.types.Material) -> Tuple[int, int, int]:
    if globs.is_blender_2_79_or_older:
        return rgb_to_255_scale(mat.diffuse_color)

    shader = shader_type(mat) if mat else False
    if shader == 'mmdCol':
        return rgb_to_255_scale(mat.node_tree.nodes['mmd_shader'].inputs['Diffuse Color'].default_value)
    elif shader == 'vrm':
        return rgb_to_255_scale(mat.node_tree.nodes['RGB'].outputs[0].default_value)
    elif shader == 'vrmCol':
        return rgb_to_255_scale(mat.node_tree.nodes['Group'].inputs[10].default_value)
    elif shader == 'diffuseCol':
        return rgb_to_255_scale(mat.node_tree.nodes['Diffuse BSDF'].inputs['Color'].default_value)
    elif shader == 'xnalaraNewCol':
        return rgb_to_255_scale(mat.node_tree.nodes['Group'].inputs['Diffuse'].default_value)
    elif shader == 'xnalaraCol':
        return rgb_to_255_scale(mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value)
    return 255, 255, 255
