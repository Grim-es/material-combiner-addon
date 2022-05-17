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


def get_material_image_or_color(mat):
    if mat:
        if globs.version > 0:
            shader = shader_type(mat) if mat else None
            if shader == 'mmd':
                node = mat.node_tree.nodes['mmd_base_tex']
            elif shader == 'vrm' or shader == 'xnalara' or shader == 'diffuse' or shader == 'emission':
                node = mat.node_tree.nodes['Image Texture']
            else:
                node = None

            if node:
                image = node.image
                if image:
                    if is_image_valid(image):
                        src = image
                    else:
                        src = get_diffuse(mat, convert_to_255_scale=False, linear=True)
                        print("DEBUG: Found image {} in {}, but it's considered invalid, so using diffuse color instead".format(image, mat))
                else:
                    # If the image from the shader is None, the Image Texture has no assigned image. If such an Image
                    # Texture node is used, it will give a black color. Technically it will give an alpha of 0.0 too, but
                    # it's possible that the alpha output isn't being used, so 1.0 alpha is probably the better choice.
                    src = (0.0, 0.0, 0.0, 1.0)
                    print("DEBUG: No image found in texture node for shader '{}' for material {}, so used Black color".format(shader, mat))
            else:
                # No node found from shader, so get the diffuse color instead
                # Pixels are normalized and read in linear, so the diffuse colors must be read as linear too
                src = get_diffuse(mat, convert_to_255_scale=False, linear=True)
                if shader:
                    print("DEBUG: Found shader '{}' for {}. But couldn't find the correct node to use. Got diffuse colour instead".format(shader, mat))
                else:
                    print("DEBUG: Unrecognised shader for {}. Got diffuse colour instead".format(mat))
        else:
            src = get_image(get_texture(mat))
            if src is None:
                src = get_diffuse(mat, convert_to_255_scale=False, linear=True)
    else:
        src = (0.0, 0.0, 0.0, 1.0)
        print("DEBUG: No material, so used Black color")
    return src


def sort_materials(mat_list):
    for mat in bpy.data.materials:
        mat.root_mat = None
    mat_dict = defaultdict(list)
    for mat in mat_list:
        material_source = get_material_image_or_color(mat)
        if isinstance(material_source, bpy.types.Image):
            material_image = material_source
            if is_single_colour_generated(material_image):
                # Generated images that are a single color can be treated as if they are just a colour
                mat_dict[tuple(material_image.generated_color)].append(mat)
            else:
                # TODO: It would be useful to differentiate between no image and an invalid image, that way, the user
                #       could be told that an image is invalid, why, and how to fix it if there is a clear fix.
                mat_dict[(material_image.name, get_diffuse(mat, convert_to_255_scale=False, linear=True) if mat.smc_diffuse else None)].append(mat)
        elif isinstance(material_source, tuple):
            # Material either has no image or the image is not considered valid
            mat_dict[material_source].append(mat)
        else:
            raise TypeError("Material sources should be images or colors, but got '{}'".format(material_source))
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
                return 255, 255, 255, 255
            else:
                return 1.0, 1.0, 1.0, 1.0
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

    # Append alpha, we do this so that if a blank color generated texture is used, which uses full RGBA, if its
    # generated color is the same as the diffuse color of a material, they can be identified as duplicates correctly
    if len(color) == 3:
        if convert_to_255_scale:
            color += (255,)
        else:
            color += (1.0,)

    return color
