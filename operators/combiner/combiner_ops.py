import math
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
from ...utils.materials import shader_type
from ...utils.materials import get_diffuse
from ...utils.materials import sort_materials
from ...utils.textures import get_texture
from ...utils.images import save_generated_image_to_file, is_image_valid
from ...utils.pixel_buffer import get_pixel_buffer, get_resized_pixel_buffer, buffer_to_image, new_pixel_buffer,\
    pixel_buffer_paste
from ...utils.textures import get_image


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
        if mat and mat.name == mat_name:
            return i


def get_size(scn, data):
    for mat, mat_data in data.items():
        if globs.version > 0:
            img = None
            shader = shader_type(mat) if mat else None
            if shader == 'mmd':
                img = mat.node_tree.nodes['mmd_base_tex'].image
            elif shader == 'vrm' or shader == 'xnalara' or shader == 'diffuse' or shader == 'emission':
                img = mat.node_tree.nodes['Image Texture'].image
        else:
            img = get_image(get_texture(mat))
        # Get max x and max y of the uvs for this material. The uvs should already be aligned such that the minimum x
        # and y are both within the bounds [0,1]
        # TODO: If all values less than 1, then 1 gets chosen as the max because of the outer max(), couldn't we crop
        #       the image to only the area that is needed? If we were to pick a margin value, we would want to make sure
        #       it doesn't add more margin than would fit in the image
        max_x = max(max([uv.x for uv in mat_data['uv'] if not math.isnan(uv.x)], default=1), 1)
        max_y = max(max([uv.y for uv in mat_data['uv'] if not math.isnan(uv.y)], default=1), 1)
        # TODO: Up to 25 copies of the same image sounds like it could be a bit high for most images, maybe it should be
        #  made lower (or even higher) based on the dimensions of the image
        mat_data['gfx']['uv_size'] = (max_x if max_x < 25 else 1, max_y if max_y < 25 else 1)
        if not scn.smc_crop:
            # FIXME: UVs are off by half a pixel. To reproduce, atlas a quad with uvs (0,0), (0,1), (1,0), (1,1).
            #        The corners of the quad's UVs will all be half a pixel towards the middle of the quad
            # FIXME: UVs do not get scaled properly when images in the atlas have to be made much smaller?
            #        Maybe something to do with resizing the atlas at the end?
            mat_data['gfx']['uv_size'] = tuple(map(math.ceil, mat_data['gfx']['uv_size']))
        if is_image_valid(img):
            if mat.smc_size:
                img_size = (min(mat.smc_size_width, img.size[0]),
                            min(mat.smc_size_height, img.size[1]))
            else:
                img_size = (img.size[0], img.size[1])
            mat_data['gfx']['size'] = tuple(
                int(s * uv_s + int(scn.smc_gaps)) for s, uv_s in zip(img_size, mat_data['gfx']['uv_size']))
        else:
            mat_data['gfx']['size'] = (scn.smc_diffuse_size + int(scn.smc_gaps),) * 2
    return OrderedDict(sorted(data.items(), key=lambda x: min(x[1]['gfx']['size']), reverse=True))


def get_uv_image(item, img_buffer, size):
    """Repeat the input image adjacent to itself enough times to ensure that the all the uvs are within the bounds of
    the image.

    :return: A new image created by repeating the input image."""
    uv_img = new_pixel_buffer(size)
    img_w = img_buffer.shape[0]
    img_h = img_buffer.shape[1]
    for w in range(math.ceil(item['gfx']['uv_size'][0])):
        for h in range(math.ceil(item['gfx']['uv_size'][1])):
            pixel_buffer_paste(uv_img, img_buffer, (
                w * img_w,
                uv_img.shape[1] - img_h - h * img_h,
                w * img_w + img_w,
                uv_img.shape[1] - img_h - h * img_h + img_h
            ))
    return uv_img


def get_gfx(scn, mat, item, src):
    size = tuple(size - int(scn.smc_gaps) for size in item['gfx']['size'])
    if isinstance(src, bpy.types.Image):
        if src:
            if mat.smc_size:
                img_buffer = get_resized_pixel_buffer(src, (mat.smc_size_width, mat.smc_size_height))
            elif tuple(src.size) != size:
                img_buffer = get_resized_pixel_buffer(src, size)
            else:
                img_buffer = get_pixel_buffer(src)
            max_uv = item['gfx']['uv_size']
            # Note that get_size(...) sets uv_size to always be at least 1
            if max_uv[0] > 1 or max_uv[1] > 1:
                img_buffer = get_uv_image(item, img_buffer, size)
            if mat.smc_diffuse:
                # TODO: This diffuse_img was in sRGB, surely this needs to be linear?
                diffuse_color = get_diffuse(mat, convert_to_255_scale=False, linear=True)
                # Multiply by the diffuse color
                # 3d slice of [all x, all y, only the first len(diffuse_color) components]
                # TODO: Could hardcode 3
                img_buffer[:, :, :len(diffuse_color)] *= diffuse_color
        else:
            # TODO: We can optimise this by passing in the colour directly
            img_buffer = new_pixel_buffer(size, get_diffuse(mat, convert_to_255_scale=False) + (1.0,))
    else:
        # src must be a color in a tuple/list of components
        # TODO: We can probably safely reject anything that isn't RGB or RGBA
        num_components = len(src)
        if num_components == 3:
            # Typical RGB only, we will assume alpha should be 1.0
            src = src + (1.0,)
        elif num_components == 2:
            # Weird to be passing in only RG, I guess we can leave the last component as 0.0
            src = src + (0.0, 1.0)
        elif num_components == 1:
            # R only, we could either spread the single component out into RGB or set G and B to 0.0.
            # Alpha will be treated as 1.0.
            # Expand single component to RGB
            # TODO: Maybe convert luminance to greyscale instead?
            src = src + (src[0], src[0], 1.0)
        elif num_components != 4:
            raise TypeError("Invalid colour '{}', must be tuple-like with at most 4 (RGBA) elements.".format(src))
        img_buffer = new_pixel_buffer(size, src)
    return img_buffer


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
                item['gfx']['img'] = mat.node_tree.nodes['mmd_base_tex'].image
            elif shader == 'vrm' or shader == 'xnalara' or shader == 'diffuse' or shader == 'emission':
                item['gfx']['img'] = mat.node_tree.nodes['Image Texture'].image
            else:
                if mat:
                    # Pixels are normalized and read in linear, so the diffuse colors must be read as linear too
                    item['gfx']['img'] = get_diffuse(mat, convert_to_255_scale=False, linear=True)
                    print("DEBUG: Unrecognised shader for {}. Got diffuse colour instead".format(mat))
                else:
                    item['gfx']['img'] = [0.0, 0.0, 0.0, 1.0]
                    print("DEBUG: No material, so used Black color")
        else:
            item['gfx']['img'] = get_image(get_texture(mat))
    img = new_pixel_buffer(size)
    for mat, i in data.items():
        if i['gfx']['fit']:
            if i['gfx']['img'] is not None:
                gfx = get_gfx(scn, mat, i, i['gfx']['img'])
                pixel_buffer_paste(img, gfx, (i['gfx']['fit']['x'] + int(scn.smc_gaps / 2),
                                              i['gfx']['fit']['y'] + int(scn.smc_gaps / 2)))
    atlas = buffer_to_image(img, name='temp_material_combine_atlas')
    if scn.smc_size == 'CUST':
        # FIXME Maybe broken?
        #  Of note, much better results would be achieved from resizing images first to match the desired packed shape
        #  as the edges of textures would not blur together
        atlas.scale(scn.smc_size_width, scn.smc_size_height)
    return atlas


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
