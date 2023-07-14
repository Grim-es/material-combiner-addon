import math
import numpy as np
import os
import re
from collections import OrderedDict
from collections import defaultdict
from itertools import chain
from typing import Tuple

import bpy
from bpy.types import Image

from ... import globs
from ...utils.objects import get_polys, get_uv, align_uv
from ...utils.materials import sort_materials
from ...utils.material_source import MaterialSource
from ...utils.images import save_generated_image_to_file, is_single_colour_generated, single_color_generated_to_color
from ...utils.pixels.pixel_buffer import (get_pixel_buffer, get_resized_pixel_buffer, buffer_to_image, new_pixel_buffer,
                                          pixel_buffer_paste, color_convert_linear_to_srgb)
from .combiner_types import RootMatData, Data, MatsUV, Structure, StructureItem
from ...utils.type_hints import Size, PixelBuffer


def set_ob_mode(context):
    for ob in (item.ob for item in context.scene.smc_ob_data if item.type == globs.C_L_OBJECT):
        if ob.mode == 'OBJECT':
            # Object is already in the correct mode, nothing to do
            continue

        # Call bpy.ops.object.mode_set, but override the active_object of the context so that the Operator acts on ob
        # instead of the currently active Object
        if globs.is_blender_3_2_or_newer:
            # The positional argument context override is deprecated as of Blender 3.2, to be replaced by
            # Context.temp_override
            with context.temp_override(active_object=ob):
                bpy.ops.object.mode_set(mode='OBJECT')
        else:
            bpy.ops.object.mode_set({'active_object': ob}, mode='OBJECT')


def get_data(data) -> Data:
    object_mats_layers = defaultdict(dict)
    for i in data:
        if i.type == globs.C_L_MATERIAL and i.used:
            object_mats_layers[i.ob.name][i.mat] = i.layer
    return object_mats_layers


def get_mats_uv(scn, data: Data) -> MatsUV:
    object_mats_uvs = {}
    for ob_n, i in data.items():
        ob = scn.objects[ob_n]
        object_mats_uvs[ob_n] = defaultdict(list)
        for material_idx, polys in get_polys(ob).items():
            mat = ob.data.materials[material_idx]
            if mat in i.keys():
                for poly in polys:
                    # Get the uvs for the object's active uv layer for this polygon
                    uvs_for_poly = get_uv(ob, poly)
                    # Offset all the uvs such that the minimum uv.x and uv.y lie within the range [0,1]
                    align_uv(uvs_for_poly)
                    # Add the uvs to the list of uvs for this material
                    object_mats_uvs[ob_n][mat].extend(uvs_for_poly)
    return object_mats_uvs


def clear_empty_mats(scn, data: Data, mats_uv: MatsUV):
    for object_name, mat_layers in data.items():
        ob = scn.objects[object_name]
        for mat in mat_layers.keys():
            if mat not in mats_uv[object_name].keys():
                mat_idx = ob.data.materials.find(mat.name)
                if globs.is_blender_2_81_or_newer:
                    ob.data.materials.pop(index=mat_idx)
                else:
                    ob.data.materials.pop(index=mat_idx, update_data=True)


def set_root_mats(mats_uv: MatsUV):
    mat_list = list(set(chain.from_iterable(mats_uv.values())))
    mat_dict = sort_materials(mat_list)
    for mats in mat_dict.values():
        for mat in mats[1:]:
            mat.root_mat = mats[0]


def get_structure(scn, data: Data, mats_uv: MatsUV) -> Structure:
    structure = {}
    for object_name, mats_layers in data.items():
        ob = scn.objects[object_name]
        for mat in mats_layers.keys():
            if mat.name in ob.data.materials:
                is_duplicate = mat.root_mat is not None
                root_mat = mat.root_mat if is_duplicate else mat
                if root_mat not in structure:
                    root_mat_data = RootMatData()
                    structure[root_mat] = root_mat_data
                else:
                    root_mat_data = structure[root_mat]
                if is_duplicate:
                    root_mat_data.duplicate_materials.add(mat.name)
                root_mat_data.objects_used_in.add(ob.name)
                root_mat_data.uv_vectors.extend(mats_uv[object_name][mat])
    return structure


def clear_duplicates(scn, structure: Structure):
    for root_mat_data in structure.values():
        for ob_n in root_mat_data.objects_used_in:
            ob = scn.objects[ob_n]
            for dup_n in root_mat_data.duplicate_materials:
                delete_material(ob, dup_n)


def delete_material(mesh_obj, mat_name: str):
    materials = mesh_obj.data.materials
    mat_idx = materials.find(mat_name)
    if mat_idx != -1:
        if globs.is_blender_2_81_or_newer:
            mesh_obj.data.materials.pop(index=mat_idx)
        else:
            mesh_obj.data.materials.pop(index=mat_idx, update_data=True)


def add_images(structure: Structure):
    for mat, mat_data in structure.items():
        mat_data.gfx.pixel_source = MaterialSource.from_material(mat)


def _size_sorting(item: StructureItem):
    mat, mat_data = item
    gfx = mat_data.gfx
    size_x, size_y = gfx.size
    src_sort = gfx.pixel_source.to_sort_key(mat.smc_diffuse)
    globs.debug_print("DEBUG: Sorting gfx {}".format(gfx))
    # Sorting order:
    # 1) maximum of x and y
    # 2) area
    # 3) x
    # 4) sort_key (image name or '' if no image, color tuple or (1,1,1,1) if no color)
    # First sort by maximum of x and y, then, if equal, next sort by area, if still equal, arbitrarily pick size_x and
    # if still equal, go by the name of the image, if there is no image, then go by color's components
    return max(size_x, size_y), size_x * size_y, size_x, src_sort


def get_size(scn, structure: Structure) -> Structure:
    for mat, mat_data in structure.items():
        gfx = mat_data.gfx
        # Get max x and max y of the uvs for this material. The uvs should already be aligned such that the minimum x
        # and y are both within the bounds [0,1]
        max_x = max(max([uv.x for uv in mat_data.uv_vectors if not math.isnan(uv.x)], default=1), 1)
        max_y = max(max([uv.y for uv in mat_data.uv_vectors if not math.isnan(uv.y)], default=1), 1)
        gfx.uv_size = (max_x if max_x < 25 else 1, max_y if max_y < 25 else 1)
        if not scn.smc_crop:
            gfx.uv_size = tuple(map(math.ceil, gfx.uv_size))
        pixel_source = gfx.pixel_source
        img = pixel_source.to_image_value()
        if img and not is_single_colour_generated(img):
            if mat.smc_size:
                img_size = (min(mat.smc_size_width, img.size[0]),
                            min(mat.smc_size_height, img.size[1]))
            else:
                img_size = (img.size[0], img.size[1])
            gfx.size = tuple(
                int(s * uv_s + int(scn.smc_gaps)) for s, uv_s in zip(img_size, gfx.uv_size))
        else:
            gfx.size = (scn.smc_diffuse_size + int(scn.smc_gaps),) * 2
    return OrderedDict(sorted(structure.items(), key=_size_sorting, reverse=True))


def get_uv_image(pixel_buffer: PixelBuffer, size: Size) -> PixelBuffer:
    """Repeat the input image adjacent to itself until a copy with the desired size is made.

    :return: A new image created by repeating the input image or the input image if no repeats are required."""
    required_x = size[0]
    required_y = size[1]
    buffer_x = pixel_buffer.shape[1]
    buffer_y = pixel_buffer.shape[0]
    if required_x > buffer_x or required_y > buffer_y:
        # The performance difference between tile and pad is odd, pad seems to scale poorly with an X pad amount
        # greater than the width of the image, but otherwise seems to be faster on average
        # Note that padded images will use less memory since their data fits the required shape exactly, whereas
        # tiled images contain an excess of pixels in their data and then a view of the data is made of only the
        # part up to the required shape.
        use_tile = required_x > 2 * buffer_x
        if use_tile:
            globs.debug_print("DEBUG: Tiling image with size {} to fit size {}".format((buffer_x, buffer_y), size))
            # Tile the image the minimum number of times until the required size fits
            x_tiles = math.ceil(required_x / buffer_x)
            y_tiles = math.ceil(required_y / buffer_y)
            tiled = np.tile(pixel_buffer, (y_tiles, x_tiles, 1))
            # The tiled image is likely to be wider or taller than needed, so view only the part that is wanted
            tiled_shrunk_view = tiled[:required_y, :required_x]
            tiled_shrunk_view_x = tiled_shrunk_view.shape[1]
            tiled_shrunk_view_y = tiled_shrunk_view.shape[0]
            if required_x != tiled_shrunk_view_x or required_y != tiled_shrunk_view_y:
                raise RuntimeError("Tiled size {} does not match required size {}".format((tiled_shrunk_view_x, tiled_shrunk_view_y), size))
            else:
                return tiled_shrunk_view
        else:
            globs.debug_print("DEBUG: Padding image with size {} to fit size {}".format((buffer_x, buffer_y), size))
            # Pad the exact amount needed onto the image to make it the required size
            pad_above = required_y - buffer_y if required_y > buffer_y else 0
            pad_below = 0
            pad_right = required_x - buffer_x if required_x > buffer_x else 0
            pad_left = 0
            padded = np.pad(pixel_buffer, ((pad_below, pad_above), (pad_left, pad_right), (0, 0)), mode='wrap')
            padded_x = padded.shape[1]
            padded_y = padded.shape[0]
            if required_x != padded_x or required_y != padded_y:
                raise RuntimeError("Padded size {} does not match required size {}".format((padded_x, padded_y), size))
            else:
                return padded
    else:
        globs.debug_print("DEBUG: Image requested to be tiled is already the correct shape ({}, {})".format(required_y, required_x))
        return pixel_buffer


def get_gfx(scn, mat, mat_data: RootMatData, src: MaterialSource, atlas_is_srgb=True) -> PixelBuffer:
    gfx = mat_data.gfx
    gfx_size_x, gfx_size_y = gfx.size
    gap = int(scn.smc_gaps)
    size = (gfx_size_x - gap, gfx_size_y - gap)
    img = src.to_image_value()
    if img:
        if is_single_colour_generated(img):
            target_colorspace = 'sRGB' if atlas_is_srgb else 'Linear'
            if mat.smc_diffuse and src.color:
                converted_color = single_color_generated_to_color(img, src.to_color_value(),
                                                                  target_colorspace=target_colorspace)
            else:
                converted_color = single_color_generated_to_color(img, target_colorspace=target_colorspace)
            # single_color_generated_to_color does the sRGB/linear conversion(s) for us so don't convert to sRGB when
            # creating the pixel buffer
            img_buffer = new_pixel_buffer(size, converted_color, read_only_rectangle=True, convert_linear_to_srgb=False)
        else:
            if mat.smc_size:
                img_buffer = get_resized_pixel_buffer(img, (mat.smc_size_width, mat.smc_size_height))
            else:
                img_buffer = get_pixel_buffer(img)
            max_uv = gfx.uv_size
            # Note that get_size(...) sets uv_size to always be at least 1
            max_uv_x = max_uv[0]
            max_uv_y = max_uv[1]
            if max_uv_x > 1 or max_uv_y > 1:
                # Tile the image adjacent to itself enough times to ensure all the uvs are within the bounds of the image
                img_buffer = get_uv_image(img_buffer, size)
            if mat.smc_diffuse and src.color:
                diffuse_color = src.to_color_value()
                diffuse_color_as_array = np.asarray(diffuse_color)
                # Colors are scene linear and need to be converted such that they will look the same when in sRGB if the
                # atlas is in sRGB
                if atlas_is_srgb:
                    globs.debug_print("DEBUG: Converting diffuse color {} for sRGB".format(diffuse_color_as_array))
                    diffuse_color_as_array = color_convert_linear_to_srgb(diffuse_color_as_array)
                    globs.debug_print("DEBUG: Converted diffuse color to {}".format(diffuse_color_as_array))
                is_not_one = diffuse_color_as_array != 1
                if is_not_one.any():
                    # Multiply by the diffuse color
                    # 3d slice of [all x, all y, only the components that aren't 1]
                    img_buffer[:, :, is_not_one] *= diffuse_color_as_array[is_not_one]
    else:
        img_buffer = new_pixel_buffer(size, src.to_color_value(), read_only_rectangle=True,
                                      convert_linear_to_srgb=atlas_is_srgb)
    return img_buffer


def get_packed_atlas_size(scn, size: Size) -> Size:
    globs.debug_print("DEBUG: Atlas input size: {}".format(size))
    if scn.smc_size == 'PO2':
        size = tuple(1 << (x - 1).bit_length() for x in size)
    elif scn.smc_size == 'QUAD':
        size = (max(size),) * 2
    globs.debug_print("DEBUG: Atlas size: {}".format(size))
    return size


def get_atlas(scn, structure: Structure, size: Size) -> Image:
    # The default color is black, which is the same in both linear and sRGB, so no need to convert
    atlas_pixel_buffer = new_pixel_buffer(size, convert_linear_to_srgb=False)
    for mat, mat_data in structure.items():
        top_left_corner = mat_data.get_top_left_corner(scn)
        if top_left_corner:
            material_pixel_buffer = get_gfx(scn, mat, mat_data, mat_data.gfx.pixel_source)
            pixel_buffer_paste(atlas_pixel_buffer, material_pixel_buffer, top_left_corner)
    atlas = buffer_to_image(atlas_pixel_buffer, name='temp_material_combine_atlas')
    if scn.smc_size == 'CUST':
        atlas_width, atlas_height = atlas.size
        max_atlas_height = scn.smc_size_height
        max_atlas_width = scn.smc_size_width
        # Uniformly scale down the image until its dimensions fit within the custom max size
        if atlas_height > max_atlas_height or atlas_width > max_atlas_width:
            height_ratio = max_atlas_height / atlas_height
            width_ratio = max_atlas_width / atlas_width
            if height_ratio < width_ratio:
                new_height = max_atlas_height
                new_width = round(atlas_width * height_ratio)
            else:
                new_width = max_atlas_width
                new_height = round(atlas_height * width_ratio)
            atlas.scale(new_width, new_height)
    return atlas


def get_aligned_uv(scn, structure: Structure, size: Size):
    for mat, mat_data in structure.items():
        gfx = mat_data.gfx
        w, h = gfx.size
        uv_w, uv_h = gfx.uv_size
        fit = gfx.fit
        for uv in mat_data.uv_vectors:
            reset_x = uv.x / uv_w * (w - 2 - int(scn.smc_gaps)) / size[0]
            reset_y = 1 + uv.y / uv_h * (h - 2 - int(scn.smc_gaps)) / size[1] - h / size[1]
            uv.x = reset_x + (fit.x + 1 + int(scn.smc_gaps / 2)) / size[0]
            uv.y = reset_y - (fit.y - 1 - int(scn.smc_gaps / 2)) / size[1]


def get_comb_mats(scn, atlas: Image, mats_uv: MatsUV):
    layers = set()
    existed_ids = set()
    for combine_list_item in scn.smc_ob_data:
        if combine_list_item.type == globs.C_L_MATERIAL:
            if combine_list_item.used and combine_list_item.mat in mats_uv[combine_list_item.ob.name]:
                layers.add(combine_list_item.layer)
    # Make sure that when we save the atlas, that it doesn't overwrite an existing file by finding all existing atlases
    # in the smc_save_path directory and extracting the unique id of each
    if os.path.isdir(scn.smc_save_path):
        # Pattern matching the 'Atlas_{0}.png'.format(unique_id) format used below when naming atlases
        atlas_file_pattern = re.compile(r"Atlas_(\d+).png")
        for file_or_directory_name in os.listdir(scn.smc_save_path):
            # Match against the full string
            match = atlas_file_pattern.fullmatch(file_or_directory_name)
            if match:
                # (\d+) is the only subgroup, so it will be at index 1 (index 0 is the fully matched string)
                existed_ids.add(int(match.group(1)))
    unique_id = 1
    while unique_id in existed_ids:
        # Add one until the id doesn't already exist
        unique_id += 1
    # Format for at least 5 digits, this keeps generated atlases in order when sorted alphabetically, up to 5 digits.
    # e.g. Atlas_10.png would be sorted alphabetically before Atlas_9.png despite typically being generated afterwards,
    # whereas Atlas_00010.png would be sorted after Atlas_00009.png
    unique_id = "{0:05d}".format(unique_id)
    atlas_name = 'Atlas_{0}.png'.format(unique_id)
    path = os.path.join(scn.smc_save_path, atlas_name)
    atlas.name = atlas_name
    save_generated_image_to_file(atlas, path, 'PNG')
    texture = bpy.data.textures.new('texture_atlas_{0}'.format(unique_id), 'IMAGE')
    texture.image = atlas
    mats = {}
    for layer in layers:
        mat = bpy.data.materials.new(name='material_atlas_{0}_{1}'.format(unique_id, layer))
        if globs.is_blender_2_80_or_newer:
            mat.blend_method = 'CLIP'
            mat.use_backface_culling = True
            mat.use_nodes = True
            node_texture = mat.node_tree.nodes.new(type='ShaderNodeTexImage')
            node_texture.image = atlas
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
        mats[layer] = mat
    return mats


def assign_comb_mats(scn, data: Data, mats_uv: MatsUV, atlas: Image):
    comb_mats = get_comb_mats(scn, atlas, mats_uv)
    for ob_n, mat_layers in data.items():
        ob = scn.objects[ob_n]
        for idx in set(mat_layers.values()):
            if idx in comb_mats.keys():
                ob.data.materials.append(comb_mats[idx])
        for idx, polys in get_polys(ob).items():
            if ob.data.materials[idx] in mat_layers.keys():
                mat_idx = ob.data.materials.find(comb_mats[mat_layers[ob.data.materials[idx]]].name)
                for poly in polys:
                    poly.material_index = mat_idx


def clear_mats(scn, mats_uv: MatsUV):
    for ob_n, i in mats_uv.items():
        ob = scn.objects[ob_n]
        for mat in i.keys():
            mat_idx = ob.data.materials.find(mat.name)
            if globs.is_blender_2_81_or_newer:
                ob.data.materials.pop(index=mat_idx)
            else:
                ob.data.materials.pop(index=mat_idx, update_data=True)
