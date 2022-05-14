import math
from collections import defaultdict

import bpy
from .images import is_image_valid, is_single_colour_generated
from .textures import get_texture, get_image
from .. import globs


def get_materials(ob):
    return [mat_slot.material for mat_slot in ob.material_slots]


def shader_type(mat):
    if (mat.node_tree and mat.node_tree.nodes and 'mmd_shader' in mat.node_tree.nodes and
            'mmd_base_tex' in mat.node_tree.nodes):
        return 'mmd'
    elif mat.node_tree and mat.node_tree.nodes and 'mmd_shader' in mat.node_tree.nodes:
        return 'mmdCol'
    elif (mat.node_tree and mat.node_tree.nodes and 'Group' in mat.node_tree.nodes and 'Image Texture' in
          mat.node_tree.nodes and mat.node_tree.nodes['Group'].node_tree.name == 'MToon_unversioned'):
        return 'vrm'
    elif (mat.node_tree and mat.node_tree.nodes and 'Group' in mat.node_tree.nodes and
          mat.node_tree.nodes['Group'].node_tree.name == 'MToon_unversioned'):
        return 'vrmCol'
    elif (mat.node_tree and mat.node_tree.nodes and 'Group' in mat.node_tree.nodes and
          mat.node_tree.nodes['Group'].node_tree.name == 'XPS Shader' and 'Image Texture' in mat.node_tree.nodes):
        return 'xnalara'
    elif (mat.node_tree and mat.node_tree.nodes and 'Group' in mat.node_tree.nodes and
          mat.node_tree.nodes['Group'].node_tree.name == 'Group'):
        return 'xnalaraNewCol'
    elif (mat.node_tree and mat.node_tree.nodes and 'Principled BSDF' in mat.node_tree.nodes and
          'Image Texture' in mat.node_tree.nodes):
        return 'xnalara'
    elif mat.node_tree and mat.node_tree.nodes and 'Principled BSDF' in mat.node_tree.nodes:
        return 'xnalaraCol'
    elif (mat.node_tree and mat.node_tree.nodes and 'Diffuse BSDF' in mat.node_tree.nodes and
          'Image Texture' in mat.node_tree.nodes):
        return 'diffuse'
    elif mat.node_tree and mat.node_tree.nodes and 'Diffuse BSDF' in mat.node_tree.nodes:
        return 'diffuseCol'
    elif (mat.node_tree and mat.node_tree.nodes and 'Emission' in mat.node_tree.nodes and
          'Image Texture' in mat.node_tree.nodes):
        return 'emission'
    elif mat.node_tree and mat.node_tree.nodes and 'Emission' in mat.node_tree.nodes:
        return 'emissionCol'


def sort_materials(mat_list):
    for mat in bpy.data.materials:
        mat.root_mat = None
    mat_dict = defaultdict(list)
    for mat in mat_list:
        if globs.version > 0:
            shader = shader_type(mat) if mat else False
            if shader == 'mmd':
                image = mat.node_tree.nodes['mmd_base_tex'].image
            elif shader == 'vrm' or shader == 'xnalara' or shader == 'diffuse' or shader == 'emission':
                image = mat.node_tree.nodes['Image Texture'].image
            else:
                image = None
        else:
            image = get_image(get_texture(mat))
        if image:
            if is_image_valid(image):
                if is_single_colour_generated(image):
                    # Generated images that are a single color can be treated as if
                    mat_dict[tuple(image.generated_color)].append(mat)
                else:
                    # TODO: It would be useful to differentiate between no image and an invalid image, that way, the user
                    #       could be told that an image is invalid, why, and how to fix it if there is a clear fix.
                    mat_dict[(image.name, get_diffuse(mat) if mat.smc_diffuse else None)].append(mat)
        else:
            # Material either has no image or the image is not considered valid
            mat_dict[get_diffuse(mat)].append(mat)
    return mat_dict


# From https://github.com/blender/blender/blob/82df48227bb7742466d429a5b465e0ada95d959d/intern/cycles/kernel/osl/shaders/node_color.h
def scene_linear_to_srgb(c):
    if c < 0.0031308:
        return 0.0 if c < 0.0 else c * 12.92
    else:
        return 1.055 * math.pow(c, 1.0 / 2.4) - 0.055


def to_255_scale(c):
    return max(min(int(c * 255 + 0.5), 255), 0)


# TODO: If we were to want to create an atlas for a data texture such as roughness, the colors should be left as linear
def get_diffuse(mat, convert_to_255_scale=True, linear=False):
    """Returns the diffuse RGB from a material,"""
    if globs.version:
        shader = shader_type(mat) if mat else False
        # Colors in shader nodes are full RGBA, but only the RGB is actually used, so we only get the first 3 components
        if shader == 'mmdCol':
            color = mat.node_tree.nodes['mmd_shader'].inputs['Diffuse Color'].default_value[:3]
        elif shader == 'vrm':
            color = mat.node_tree.nodes['RGB'].outputs[0].default_value[:3]
        elif shader == 'vrmCol':
            color = mat.node_tree.nodes['Group'].inputs[10].default_value[:3]
        elif shader == 'diffuseCol':
            color = mat.node_tree.nodes['Diffuse BSDF'].inputs['Color'].default_value[:3]
        elif shader == 'xnalaraNewCol':
            color = mat.node_tree.nodes['Group'].inputs['Diffuse'].default_value[:3]
        elif shader == 'xnalaraCol':
            color = mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value[:3]
        else:
            # White is the same in both linear and srgb, so no conversion is needed
            if convert_to_255_scale:
                return 255, 255, 255
            else:
                return 1.0, 1.0, 1.0
    else:
        color = tuple(mat.diffuse_color)

    # Shader node colors are linear
    convert_to_srgb = not linear
    if convert_to_srgb:
        color = map(scene_linear_to_srgb, color)
    # We may want the colors in a 0-255 scale
    if convert_to_255_scale:
        color = tuple(map(to_255_scale, color))
    elif convert_to_srgb:
        # If we converted to srgb, color will be left as an iterable map object, so it needs converting back to a tuple
        color = tuple(color)

    return color
