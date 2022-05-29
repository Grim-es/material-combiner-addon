import math
import numpy as np
import os
import random
from collections import OrderedDict
from collections import defaultdict

import bpy

from ... import globs
from ...utils.objects import get_obs
from ...utils.objects import get_polys
from ...utils.objects import get_uv
from ...utils.objects import align_uv
from ...utils.materials import get_material_image_or_color
from ...utils.materials import get_diffuse
from ...utils.materials import sort_materials
from ...utils.images import save_generated_image_to_file, is_image_valid
from ...utils.pixels.pixel_buffer import get_pixel_buffer, get_resized_pixel_buffer, buffer_to_image, new_pixel_buffer,\
    pixel_buffer_paste


def set_ob_mode(scn):
    obs = get_obs(scn.objects)
    for ob in obs:
        scn.objects.active = ob
        bpy.ops.object.mode_set(mode='OBJECT')


def get_data(data):
    mats = defaultdict(dict)
    for i in data:
        if i.type == globs.C_L_MATERIAL and i.used:
            mats[i.ob.name][i.mat] = i.layer
    return mats


def get_mats_uv(scn, ob_mats):
    mats_uv = {}
    for ob_n, i in ob_mats.items():
        ob = scn.objects[ob_n]
        mats_uv[ob_n] = defaultdict(list)
        # TODO: Optimise performance with numpy
        for material_idx, polys in get_polys(ob).items():
            mat = ob.data.materials[material_idx]
            if mat in i.keys():
                for poly in polys:
                    # Get the uvs for the object's active uv layer for this polygon
                    uvs_for_poly = get_uv(ob, poly)
                    # Offset all the uvs such that the minimum uv.x and uv.y lie within the range [0,1]
                    align_uv(uvs_for_poly)
                    # Add the uvs to the list of uvs for this material
                    mats_uv[ob_n][mat].extend(uvs_for_poly)
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


def set_root_mats(mats_uv):
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
                is_duplicate = mat.root_mat is not None
                root_mat = mat.root_mat if is_duplicate else mat
                if root_mat not in structure:
                    root_mat_data = {
                        'gfx': {
                            'img': None,
                            'size': (),
                            'uv_size': ()
                        },
                        'dup': [],
                        'ob': [],
                        'uv': []
                    }
                    structure[root_mat] = root_mat_data
                else:
                    root_mat_data = structure[root_mat]
                if is_duplicate:
                    duplicate_mats = root_mat_data['dup']
                    if mat.name not in duplicate_mats:
                        duplicate_mats.append(mat.name)
                root_mat_objects = root_mat_data['ob']
                if ob.name not in root_mat_objects:
                    root_mat_objects.append(ob.name)
                root_mat_data['uv'].extend(mats_uv[ob_n][mat])
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
        if mat and mat.name == mat_name:
            return i


def add_images(data):
    for mat, mat_data in data.items():
        mat_data['gfx']['img'] = get_material_image_or_color(mat)


def size_sorting(item):
    _key, value = item
    gfx = value['gfx']
    size_x, size_y = gfx['size']
    img = gfx['img']
    print("DEBUG: Sorting gfx {}".format(gfx))
    if isinstance(img, bpy.types.Image):
        img_sort = img.name
        color_sort = 0
    else:
        # Should be a colour
        img_sort = ''
        color_sort = sum(img)
    # Sorting order:
    # 1) maximum of x and y
    # 2) area
    # 3) x
    # 4) image name (colors treated as '')
    # 5) sum of colour components (images treated as 0, though images should always have unique names unless included
    #    multiple times)
    # First sort by maximum of x and y, then, if equal, next sort by area, if still equal, arbitrarily pick size_x and
    # if still equal, go by the name of the image, if there is no image, then go by the sum of the color's components
    return max(size_x, size_y), size_x * size_y, size_x, img_sort, color_sort


def get_size(scn, data):
    for mat, mat_data in data.items():
        gfx = mat_data['gfx']
        img = gfx['img']
        # Get max x and max y of the uvs for this material. The uvs should already be aligned such that the minimum x
        # and y are both within the bounds [0,1]
        # TODO: If all values less than 1, then 1 gets chosen as the max because of the outer max(), couldn't we crop
        #       the image to only the area that is needed? If we were to pick a margin value, we would want to make sure
        #       it doesn't add more margin than would fit in the image
        max_x = max(max([uv.x for uv in mat_data['uv'] if not math.isnan(uv.x)], default=1), 1)
        max_y = max(max([uv.y for uv in mat_data['uv'] if not math.isnan(uv.y)], default=1), 1)
        # TODO: Up to 25 copies of the same image sounds like it could be a bit high for most images, maybe it should be
        #  made lower (or even higher) based on the dimensions of the image
        gfx['uv_size'] = (max_x if max_x < 25 else 1, max_y if max_y < 25 else 1)
        if not scn.smc_crop:
            # FIXME: UVs are off by half a pixel. To reproduce, atlas a quad with uvs (0,0), (0,1), (1,0), (1,1).
            #        The corners of the quad's UVs will all be half a pixel towards the middle of the quad
            gfx['uv_size'] = tuple(map(math.ceil, gfx['uv_size']))
        if isinstance(img, bpy.types.Image) and is_image_valid(img):
            if mat.smc_size:
                img_size = (min(mat.smc_size_width, img.size[0]),
                            min(mat.smc_size_height, img.size[1]))
            else:
                img_size = (img.size[0], img.size[1])
            gfx['size'] = tuple(
                int(s * uv_s + int(scn.smc_gaps)) for s, uv_s in zip(img_size, gfx['uv_size']))
        else:
            gfx['size'] = (scn.smc_diffuse_size + int(scn.smc_gaps),) * 2
    return OrderedDict(sorted(data.items(), key=size_sorting, reverse=True))


# TODO: It might be better to do the whole uv_image thing when pasting to the atlas instead of creating a new buffer
#       as an intermediary.
# TODO: Cropping images by UV (scene.smc_crop) only crops when uvs extend out of bounds upwards or to the right, it
#  would be beneficial to also crop to the left and downwards.
#  As a separate option, it might even be good to crop within the standard [0,1] uv bounds
def get_uv_image(img_buffer, size):
    """Repeat the input image adjacent to itself until a copy with the desired size is made.

    :return: A new image created by repeating the input image or the input image if no repeats are required."""
    required_x = size[0]
    required_y = size[1]
    buffer_x = img_buffer.shape[1]
    buffer_y = img_buffer.shape[0]
    if required_x != buffer_x or required_y != buffer_y:
        # Shrinking is not currently in use, but is here for implementation reference
        # # If the required dimension is smaller than the buffer's current dimension, take a view of the buffer with size
        # # shrunk towards the bottom left corner
        # shrink = False
        # if required_y < buffer_y:
        #     shrink = True
        #     y_slice = slice(None, required_y)
        # else:
        #     y_slice = slice(None)
        # if required_x < buffer_x:
        #     shrink = True
        #     x_slice = slice(None, required_x)
        # else:
        #     x_slice = slice(None)
        #
        # if shrink:
        #     img_buffer = img_buffer[y_slice, x_slice]

        if required_x > buffer_x or required_y > buffer_y:
            # The performance difference between tile and pad is odd, pad seems to scale poorly with an X pad amount
            # greater than the width of the image, but otherwise seems to be faster on average
            # Note that padded images will use less memory since their data fits the required shape exactly, whereas
            # tiled images contain an excess of pixels in their data and then a view of the data is made of only the
            # part up to the required shape.
            use_tile = required_x > 2 * buffer_x
            if use_tile:
                print("DEBUG: Tiling image with size {} to fit size {}".format((buffer_x, buffer_y), size))
                # Tile the image the minimum number of times until the required size fits
                x_tiles = math.ceil(required_x / buffer_x)
                y_tiles = math.ceil(required_y / buffer_y)
                tiled = np.tile(img_buffer, (y_tiles, x_tiles, 1))
                # The tiled image is likely to be wider or taller than needed, so view only the part that is wanted
                tiled_shrunk_view = tiled[:required_y, :required_x]
                tiled_shrunk_view_x = tiled_shrunk_view.shape[1]
                tiled_shrunk_view_y = tiled_shrunk_view.shape[0]
                if required_x != tiled_shrunk_view_x or required_y != tiled_shrunk_view_y:
                    raise RuntimeError("Tiled size {} does not match required size {}".format((tiled_shrunk_view_x, tiled_shrunk_view_y), size))
                else:
                    return tiled_shrunk_view
            else:
                print("DEBUG: Padding image with size {} to fit size {}".format((buffer_x, buffer_y), size))
                # Pad the exact amount needed onto the image to make it the required size
                pad_above = required_y - buffer_y if required_y > buffer_y else 0
                pad_below = 0
                pad_right = required_x - buffer_x if required_x > buffer_x else 0
                pad_left = 0
                padded = np.pad(img_buffer, ((pad_below, pad_above), (pad_left, pad_right), (0, 0)), mode='wrap')
                padded_x = padded.shape[1]
                padded_y = padded.shape[0]
                if required_x != padded_x or required_y != padded_y:
                    raise RuntimeError("Padded size {} does not match required size {}".format((padded_x, padded_y), size))
                else:
                    return padded
        else:
            return img_buffer
    else:
        print("DEBUG: Image requested to be tiled is already the correct shape ({}, {})".format(required_y, required_x))
        return img_buffer


def get_gfx(scn, mat, item, src):
    size = tuple(size - int(scn.smc_gaps) for size in item['gfx']['size'])
    if isinstance(src, bpy.types.Image):
        if mat.smc_size:
            img_buffer = get_resized_pixel_buffer(src, (mat.smc_size_width, mat.smc_size_height))
        else:
            img_buffer = get_pixel_buffer(src)
        max_uv = item['gfx']['uv_size']
        # Note that get_size(...) sets uv_size to always be at least 1
        max_uv_x = max_uv[0]
        max_uv_y = max_uv[1]
        if max_uv_x > 1 or max_uv_y > 1:
            # Tile the image adjacent to itself enough times to ensure all the uvs are within the bounds of the image
            img_buffer = get_uv_image(img_buffer, size)
        if mat.smc_diffuse:
            diffuse_color = get_diffuse(mat)
            # Multiply by the diffuse color
            # 3d slice of [all x, all y, only the first len(diffuse_color) components]
            # TODO: Could hardcode 4
            img_buffer[:, :, :len(diffuse_color)] *= diffuse_color
    else:
        # src must be a color in a tuple/list of components
        if len(src) != 4:
            raise TypeError("Invalid colour '{}', must be tuple-like with 4 elements (RGBA).".format(src))
        img_buffer = new_pixel_buffer(size, src, read_only_rectangle=True)
    return img_buffer


def get_atlas(scn, data, size):
    if scn.smc_size == 'PO2':
        size = tuple(1 << (x - 1).bit_length() for x in size)
    elif scn.smc_size == 'QUAD':
        size = (max(size),) * 2
    img = new_pixel_buffer(size)
    for mat, i in data.items():
        if i['gfx']['fit']:
            gfx = get_gfx(scn, mat, i, i['gfx']['img'])
            pixel_buffer_paste(img, gfx, (i['gfx']['fit']['x'] + int(scn.smc_gaps / 2),
                                          i['gfx']['fit']['y'] + int(scn.smc_gaps / 2)))
    atlas = buffer_to_image(img, name='temp_material_combine_atlas')
    if scn.smc_size == 'CUST':
        # TODO: Much better results would be achieved from resizing images first to match the desired packed shape
        #  as the edges of textures would not blur together
        atlas_width = atlas.size[0]
        atlas_height = atlas.size[1]
        max_atlas_height = scn.smc_size_height
        max_atlas_width = scn.smc_size_width
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
    return atlas, size


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
    layers = set()
    existed_ids = set()
    for combine_list_item in scn.smc_ob_data:
        if combine_list_item.type == globs.C_L_MATERIAL:
            if combine_list_item.used and combine_list_item.mat in mats_uv[combine_list_item.ob.name]:
                layers.add(combine_list_item.layer)
            mat_name = combine_list_item.mat.name
            if mat_name.startswith('material_atlas_'):
                existed_id = int(mat_name.split('_')[-2])
                existed_ids.add(existed_id)
    available_ids = set(range(10000, 99999)) - existed_ids
    unique_id = random.choice(list(available_ids))
    atlas_name = 'Atlas_{0}.png'.format(unique_id)
    path = os.path.join(scn.smc_save_path, atlas_name)
    atlas.name = atlas_name
    save_generated_image_to_file(atlas, path, 'PNG')
    texture = bpy.data.textures.new('texture_atlas_{0}'.format(unique_id), 'IMAGE')
    texture.image = atlas
    mats = {}
    for layer in layers:
        mat = bpy.data.materials.new(name='material_atlas_{0}_{1}'.format(unique_id, layer))
        if globs.version > 0:
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
