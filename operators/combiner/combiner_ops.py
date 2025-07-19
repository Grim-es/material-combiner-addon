"""Core operations for combining materials and textures.

This module implements the core functionality for the Material Combiner addon,
including UV mapping analysis, texture extraction, atlas generation, and
material assignment. It handles the complex process of creating optimized
texture atlases from multiple materials while preserving texture quality
and proper UV mapping.

Typical usage example:
    # Running the operator directly (requires directory parameter)
    bpy.ops.smc.combiner(directory=r"/path/to/save/directory")

Note: When running the operator directly (not from the addon's UI),
the `directory` parameter is required to specify where the atlas image will be saved.
"""

import io
import itertools
import math
import os
import random
import re
from collections import OrderedDict, defaultdict
from itertools import chain
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union, cast

import bpy
import numpy as np

from ...globs import (
    CombineListTypes,
    is_blender_legacy,
    is_blender_modern,
)
from ...type_annotations import (
    CombMats,
    Diffuse,
    MatsUV,
    ObMats,
    Scene,
    SMCObData,
    SMCObDataItem,
    Structure,
    StructureItem,
)
from ...utils.images import get_image, get_packed_file
from ...utils.materials import (
    get_diffuse,
    get_image_from_material,
    sort_materials,
)
from ...utils.objects import align_uv, get_polys, get_uv
from ...utils.textures import get_texture

Image = None
ImageChops = None
ImageFile = None
ImageType = None
resampling = None

try:
    from PIL import Image, ImageChops, ImageFile

    ImageType = Image.Image

    Image.MAX_IMAGE_PIXELS = None
    try:
        resampling = Image.LANCZOS
    except AttributeError:
        resampling = Image.ANTIALIAS

    if ImageFile:
        ImageFile.LOAD_TRUNCATED_IMAGES = True
except ImportError:
    pass

atlas_prefix = 'Atlas_'
atlas_texture_prefix = 'texture_atlas_'
atlas_material_prefix = 'material_atlas_'


def validate_ob_data(data: Sequence[bpy.types.PropertyGroup]) -> Optional[Dict[str, Any]]:
    """Validates that the input data contains at least one object.

    Args:
        data: Collection of property group items.

    Returns:
        None if validation passes, otherwise a dictionary with status.
    """
    return None if any(item.type == CombineListTypes.OBJECT for item in data) else {'CANCELLED'}


def set_ob_mode(scn: Scene, data: SMCObData) -> None:
    """Set active object to Object mode.

    Args:
        scn: Current scene or view layer.
        data: Dictionary of object data items.
    """
    ob = next((item.ob for item in data if item.type == CombineListTypes.OBJECT), None)
    if ob:
        scn.objects.active = ob
        bpy.ops.object.mode_set(mode='OBJECT')


def get_data(data: Sequence[bpy.types.PropertyGroup]) -> SMCObData:
    """Extract material data from property group items.

    Builds a dictionary mapping object names to their materials and respective layers.

    Args:
        data: Collection of property group items.

    Returns:
        Dictionary mapping object names to their materials with layer numbers.
    """
    mats = defaultdict(dict)
    for item in data:
        if item.type == CombineListTypes.MATERIAL and item.used:
            mats[item.ob.name][item.mat] = item.layer
    return mats


def get_mats_uv(scn: Scene, data: SMCObData) -> MatsUV:
    """Get UV coordinates for all selected materials.

    Extracts and aligns UV coordinates from all polygons using the selected
    materials in each object.

    Args:
        scn: Current scene.
        data: Dictionary mapping object names to materials.

    Returns:
        Dictionary mapping object names to materials with UV coordinates.
    """
    mats_uv = defaultdict(lambda: defaultdict(list))
    for ob_n, item in data.items():
        ob = scn.objects[ob_n]
        for idx, polys in get_polys(ob).items():
            mat = ob.data.materials[idx]
            if mat not in item:
                continue
            for poly in polys:
                mats_uv[ob_n][mat].extend(align_uv(get_uv(ob, poly)))
    return mats_uv


def clear_empty_mats(scn: Scene, data: SMCObData, mats_uv: MatsUV) -> None:
    """Remove materials without valid UV coordinates.

    Args:
        scn: Current scene.
        data: Dictionary mapping object names to materials.
        mats_uv: Dictionary mapping object names to materials with UV coordinates.
    """
    for ob_n, item in data.items():
        ob = scn.objects[ob_n]
        for mat in item:
            if mat not in mats_uv[ob_n]:
                _delete_material(ob, mat.name)


def _delete_material(ob: bpy.types.Object, name: str) -> None:
    """Remove a material from an object.

    Args:
        ob: Object to remove material from.
        name: Name of the material to remove.
    """
    if ob.type == 'MESH':
        mat_idx = ob.data.materials.find(name)
        if mat_idx >= 0:
            if is_blender_modern:
                ob.data.materials.pop(index=mat_idx)
            else:
                ob.data.materials.pop(index=mat_idx, update_data=True)


def get_duplicates(mats_uv: MatsUV) -> None:
    """Identify and mark duplicate materials.

    Finds visually identical materials and marks duplicates by setting
    their root_mat property to the first matching material.

    Args:
        mats_uv: Dictionary mapping object names to materials with UV coordinates.
    """
    mat_list = list(chain.from_iterable(mats_uv.values()))
    sorted_mat_list = sort_materials(mat_list)
    for mats in sorted_mat_list:
        root_mat = mats[0]
        for mat in mats[1:]:
            mat.root_mat = root_mat


def get_structure(scn: Scene, data: SMCObData, mats_uv: MatsUV) -> Structure:
    """Build the structure for atlas generation.

    Creates a dictionary mapping materials to their metadata, including
    graphics info, duplicate materials, objects that use them, and UV coordinates.

    Args:
        scn: Current scene.
        data: Dictionary mapping object names to materials.
        mats_uv: Dictionary mapping object names to materials with UV coordinates.

    Returns:
        Dictionary mapping materials to their metadata.
    """
    structure = defaultdict(lambda: {
        'gfx': {
            'img_or_color': None,
            'size': (),
            'uv_size': ()
        },
        'dup': [],
        'ob': [],
        'uv': []
    })

    for ob_n, item in data.items():
        ob = scn.objects[ob_n]
        for mat in item:
            if mat.name not in ob.data.materials:
                continue
            root_mat = mat.root_mat or mat
            if mat.root_mat and mat.root_mat != mat and mat.name not in structure[root_mat]['dup']:
                structure[root_mat]['dup'].append(mat.name)
            if ob.name not in structure[root_mat]['ob']:
                structure[root_mat]['ob'].append(ob.name)
            structure[root_mat]['uv'].extend(mats_uv[ob_n][mat])
    return structure

def get_size(scn: Scene, data: Structure) -> Dict:
    """Calculate sizes for all material textures.

    Determines the dimensions of each texture based on UV coordinates
    and the material's settings.

    Args:
        scn: Current scene.
        data: Dictionary mapping materials to their metadata.

    Returns:
        Sorted dictionary of materials with size information.
    """
    for mat, item in data.items():
        img = _get_image(mat)
        packed_file = get_packed_file(img)
        max_x, max_y = _get_max_uv_coordinates(item['uv'])
        item['gfx']['uv_size'] = (np.clip(max_x, 1, 25), np.clip(max_y, 1, 25))

        if not scn.smc_crop:
            item['gfx']['uv_size'] = tuple(math.ceil(x) for x in item['gfx']['uv_size'])

        if packed_file:
            img_size = _get_image_size(mat, img)
            item['gfx']['size'] = _calculate_size(img_size, item['gfx']['uv_size'], scn.smc_gaps)
        else:
            item['gfx']['size'] = (scn.smc_diffuse_size + scn.smc_gaps,) * 2

    return OrderedDict(sorted(data.items(), key=_size_sorting, reverse=True))


def _size_sorting(item: Sequence[StructureItem]) -> Tuple[int, int, int, Union[str, Diffuse, None]]:
    """Key function for sorting materials by size.

    Args:
        item: Material and its metadata.

    Returns:
        Tuple of sorting keys (max dimension, area, width, name/color).
    """
    gfx = item[1]['gfx']
    size_x, size_y = gfx['size']

    img_or_color = gfx['img_or_color']
    name_or_color = None
    if isinstance(img_or_color, tuple):
        name_or_color = gfx['img_or_color']
    elif isinstance(img_or_color, bpy.types.PackedFile):
        name_or_color = img_or_color.id_data.name

    return max(size_x, size_y), size_x * size_y, size_x, name_or_color


def _get_image(mat: bpy.types.Material) -> Union[bpy.types.Image, None]:
    """Get image from a material, handling different Blender versions.

    Args:
        mat: Material to extract image from.

    Returns:
        Image from the material or None if not found.
    """
    if is_blender_legacy:
        return get_image(get_texture(mat))

    return get_image_from_material(mat)


def _get_image_size(mat: bpy.types.Material, img: bpy.types.Image) -> Tuple[int, int]:
    """Get the size of an image, respecting material size constraints.

    Args:
        mat: Material containing the image.
        img: Image to get size from.

    Returns:
        Tuple of (width, height) dimensions.
    """
    return (
        (
            min(mat.smc_size_width, img.size[0]),
            min(mat.smc_size_height, img.size[1]),
        )
        if mat.smc_size
        else cast(Tuple[int, int], img.size)
    )


def _get_max_uv_coordinates(uv_loops: List[bpy.types.MeshUVLoop]) -> Tuple[float, float]:
    """Find the maximum UV coordinates across a list of UV loops.

    Args:
        uv_loops: List of UV coordinate vectors.

    Returns:
        Tuple of (max_x, max_y) values.
    """
    max_x = 1
    max_y = 1

    for uv in uv_loops:
        if not math.isnan(uv.x):
            max_x = max(max_x, uv.x)
        if not math.isnan(uv.y):
            max_y = max(max_y, uv.y)

    return max_x, max_y


def _calculate_size(img_size: Tuple[int, int], uv_size: Tuple[int, int], gaps: int) -> Tuple[int, int]:
    """Calculate the size needed for a texture in the atlas.

    Args:
        img_size: Original image dimensions.
        uv_size: UV coordinate range.
        gaps: Padding between textures.

    Returns:
        Tuple of (width, height) dimensions for the atlas texture.
    """
    return cast(Tuple[int, int], tuple(s * uv_s + gaps for s, uv_s in zip(img_size, uv_size)))


def get_atlas_size(structure: Structure) -> Tuple[int, int]:
    """Calculate the total size needed for the atlas.

    Args:
        structure: Dictionary mapping materials to their metadata.

    Returns:
        Tuple of (width, height) dimensions for the atlas.
    """
    max_x = 1
    max_y = 1

    for item in structure.values():
        max_x = max(max_x, item['gfx']['fit']['x'] + item['gfx']['size'][0])
        max_y = max(max_y, item['gfx']['fit']['y'] + item['gfx']['size'][1])

    return int(max_x), int(max_y)


def calculate_adjusted_size(scn: Scene, size: Tuple[int, int]) -> Tuple[int, int]:
    """Adjust atlas size based on the chosen sizing strategy.

    Args:
        scn: Current scene with atlas size settings.
        size: Original calculated size.

    Returns:
        Adjusted size based on the selected size strategy.
    """
    if scn.smc_size == 'PO2':
        return cast(Tuple[int, int], tuple(1 << int(x - 1).bit_length() for x in size))
    elif scn.smc_size == 'QUAD':
        return (int(max(size)),) * 2
    return size


def get_atlas(scn: Scene, data: Structure, atlas_size: Tuple[int, int]) -> ImageType:
    """Generate the texture atlas image.

    Creates a new image with all textures positioned according to their
    calculated fit positions.

    Args:
        scn: Current scene.
        data: Dictionary mapping materials to their metadata.
        atlas_size: Dimensions for the atlas.

    Returns:
        Generated atlas image.
    """
    smc_size = (scn.smc_size_width, scn.smc_size_height)
    img = Image.new('RGBA', atlas_size)
    half_gaps = int(scn.smc_gaps / 2)

    for mat, item in data.items():
        _set_image_or_color(item, mat)
        _paste_gfx(scn, item, mat, img, half_gaps)

    if scn.smc_size in ['CUST', 'STRICTCUST']:
        img.thumbnail(smc_size, resampling)

    if scn.smc_size == 'STRICTCUST':
        canvas_img = Image.new('RGBA', smc_size)
        canvas_img.paste(img)
        return canvas_img

    return img


def _set_image_or_color(item: StructureItem, mat: bpy.types.Material) -> None:
    """Set the image or color data for a material.

    Args:
        item: Material metadata.
        mat: Material to extract image or color from.
    """
    if is_blender_modern:
        image = get_image_from_material(mat)
        item['gfx']['img_or_color'] = get_packed_file(image) if image else None
    else:
        item['gfx']['img_or_color'] = get_packed_file(get_image(get_texture(mat)))

    if not item['gfx']['img_or_color']:
        item['gfx']['img_or_color'] = get_diffuse(mat)


def _paste_gfx(scn: Scene, item: StructureItem, mat: bpy.types.Material, img: ImageType, half_gaps: int) -> None:
    """Paste a material's graphics onto the atlas.

    Args:
        scn: Current scene.
        item: Material metadata.
        mat: Material providing the graphics.
        img: Atlas image to paste onto.
        half_gaps: Half the padding size between textures.
    """
    if not item['gfx']['fit']:
        return

    img.paste(
        _get_gfx(scn, mat, item, item['gfx']['img_or_color']),
        (int(item['gfx']['fit']['x'] + half_gaps), int(item['gfx']['fit']['y'] + half_gaps))
    )


def _get_gfx(scn: Scene, mat: bpy.types.Material, item: StructureItem,
             img_or_color: Union[bpy.types.PackedFile, Tuple, None]) -> ImageType:
    """Generate image data for a material.

    Creates an appropriate image based on whether the material has a texture
    or just a color.

    Args:
        scn: Current scene.
        mat: Material to process.
        item: Material metadata.
        img_or_color: Image data or color tuple.

    Returns:
        PIL Image to paste onto the atlas.
    """
    size = cast(Tuple[int, int], tuple(int(size - scn.smc_gaps) for size in item['gfx']['size']))

    if not img_or_color:
        return Image.new('RGBA', size, (1, 1, 1, 1))

    if isinstance(img_or_color, tuple):
        return Image.new('RGBA', size, img_or_color)

    img = Image.open(io.BytesIO(img_or_color.data)).convert("RGBA")
    if img.size != size:
        img.resize(size, resampling)
    if mat.smc_size:
        img.thumbnail((mat.smc_size_width, mat.smc_size_height), resampling)
    if max(item['gfx']['uv_size'], default=0) > 1:
        img = _get_uv_image(item, img, size)
    if mat.smc_diffuse:
        diffuse_img = Image.new(img.mode, size, get_diffuse(mat))
        img = ImageChops.multiply(img, diffuse_img)

    return img


def _get_uv_image(item: StructureItem, img: ImageType, size: Tuple[int, int]) -> ImageType:
    """Create a tiled image based on UV coordinates.

    For UVs that extend beyond the 0-1 range, this creates a tiled image
    that repeats the texture appropriately.

    Args:
        item: Material metadata.
        img: Source image to tile.
        size: Output size.

    Returns:
        Tiled image.
    """
    uv_img = Image.new('RGBA', size)
    size_height = size[1]
    img_width, img_height = img.size
    uv_width, uv_height = (math.ceil(x) for x in item['gfx']['uv_size'])

    for h in range(uv_height):
        y = size_height - img_height - h * img_height
        for w in range(uv_width):
            x = w * img_width
            uv_img.paste(img, (x, y))

    return uv_img


def align_uvs(scn: Scene, data: Structure, atlas_size: Tuple[int, int], size: Tuple[int, int]) -> None:
    """Align UV coordinates to the atlas positions.

    Transforms UV coordinates to match their new positions in the atlas.

    Args:
        scn: Current scene.
        data: Dictionary mapping materials to their metadata.
        atlas_size: Dimensions of the atlas.
        size: Original calculated size before adjustment.
    """
    size_width, size_height = size

    scaled_width, scaled_height = _get_scale_factors(atlas_size, size)

    margin = scn.smc_gaps + (0 if scn.smc_pixel_art else 2)
    border_margin = int(scn.smc_gaps / 2) + (0 if scn.smc_pixel_art else 1)

    for item in data.values():
        gfx_size = item['gfx']['size']
        gfx_height = gfx_size[1]

        gfx_width_margin, gfx_height_margin = (x - margin for x in gfx_size)

        uv_width, uv_height = item['gfx']['uv_size']

        x_offset = item['gfx']['fit']['x'] + border_margin
        y_offset = item['gfx']['fit']['y'] - border_margin

        for uv in item['uv']:
            reset_x = uv.x / uv_width * gfx_width_margin
            reset_y = uv.y / uv_height * gfx_height_margin - gfx_height

            uv_x = (reset_x + x_offset) / size_width
            uv_y = (reset_y - y_offset) / size_height

            uv.x = uv_x * scaled_width
            uv.y = uv_y * scaled_height + 1


def _get_scale_factors(atlas_size: Tuple[int, int], size: Tuple[int, int]) -> Tuple[float, float]:
    """Calculate scale factors between original and adjusted atlas sizes.

    Args:
        atlas_size: Dimensions of the atlas.
        size: Original calculated size before adjustment.

    Returns:
        Tuple of (width_factor, height_factor) scaling values.
    """
    scaled_factors = tuple(x / y for x, y in zip(size, atlas_size))

    if all(factor <= 1 for factor in scaled_factors):
        return cast(Tuple[float, float], scaled_factors)

    atlas_width, atlas_height = atlas_size
    size_width, size_height = size

    aspect_ratio = (size_width * atlas_height) / (size_height * atlas_width)
    return (1, 1 / aspect_ratio) if aspect_ratio > 1 else (aspect_ratio, 1)


def get_comb_mats(scn: Scene, atlas: ImageType, mats_uv: MatsUV) -> CombMats:
    """Create materials for the generated atlas.

    Args:
        scn: Current scene.
        atlas: Generated atlas image.
        mats_uv: Dictionary mapping object names to materials with UV coordinates.

    Returns:
        Dictionary mapping layer indices to materials.
    """
    unique_id = _get_unique_id(scn)
    layers = _get_layers(scn, mats_uv)
    path = _save_atlas(scn, atlas, unique_id)
    texture = _create_texture(path, unique_id)
    return cast(CombMats, {idx: _create_material(texture, unique_id, idx) for idx in layers})


def _get_layers(scn: Scene, mats_uv: MatsUV) -> Set[int]:
    """Get all unique layer indices from selected materials.

    Args:
        scn: Current scene.
        mats_uv: Dictionary mapping object names to materials with UV coordinates.

    Returns:
        Set of unique layer indices.
    """
    return {
        item.layer
        for item in scn.smc_ob_data
        if item.type == CombineListTypes.MATERIAL and item.used and item.mat in mats_uv[item.ob.name]
    }


def _get_unique_id(scn: Scene) -> str:
    """Generate a unique ID for the atlas.

    Args:
        scn: Current scene.

    Returns:
        Unique ID string for the atlas.
    """
    existed_ids = set()
    _add_its_from_existing_materials(scn, existed_ids)

    if not os.path.isdir(scn.smc_save_path):
        return _generate_random_unique_id(existed_ids)

    _add_ids_from_existing_files(scn, existed_ids)
    unique_id = next(x for x in itertools.count(start=1) if x not in existed_ids)
    return '{:05d}'.format(unique_id)


def _add_its_from_existing_materials(scn: Scene, existed_ids: Set[int]) -> None:
    """Add IDs from existing atlas materials to the set.

    Args:
        scn: The current scene.
        existed_ids: Set to add IDs to.
    """
    atlas_material_pattern = re.compile(r'{}(\d+)_\d+'.format(atlas_material_prefix))
    for item in scn.smc_ob_data:
        if item.type != CombineListTypes.MATERIAL:
            continue

        match = atlas_material_pattern.fullmatch(item.mat.name)
        if match:
            existed_ids.add(int(match.group(1)))


def _generate_random_unique_id(existed_ids: Set[int]) -> str:
    """Generate a random unique ID.

    Args:
        existed_ids: Set of existing IDs to avoid.

    Returns:
        Random unique ID string.
    """
    unused_ids = set(range(10000, 99999)) - existed_ids
    return str(random.choice(list(unused_ids)))


def _add_ids_from_existing_files(scn: Scene, existed_ids: Set[int]) -> None:
    """Add IDs from existing atlas files to the set.

    Args:
        scn: The current scene.
        existed_ids: Set to add IDs to.
    """
    atlas_file_pattern = re.compile(r'{}(\d+).png'.format(atlas_prefix))
    for file_name in os.listdir(scn.smc_save_path):
        match = atlas_file_pattern.fullmatch(file_name)
        if match:
            existed_ids.add(int(match.group(1)))


def _save_atlas(scn: Scene, atlas: ImageType, unique_id: str) -> str:
    """Save the atlas image to disk.

    Args:
        scn: Current scene.
        atlas: Generated atlas image.
        unique_id: Unique ID for the atlas.

    Returns:
        Path to the saved atlas image.
    """
    path = os.path.join(scn.smc_save_path, '{}{}.png'.format(atlas_prefix, unique_id))
    atlas.save(path)
    return path


def _create_texture(path: str, unique_id: str) -> bpy.types.Texture:
    """Create a Blender texture from the atlas image.

    Args:
        path: Path to the atlas image.
        unique_id: Unique ID for the atlas.

    Returns:
        Created Blender texture.
    """
    texture = bpy.data.textures.new('{}{}'.format(atlas_texture_prefix, unique_id), 'IMAGE')
    image = bpy.data.images.load(path)
    texture.image = image
    return texture


def _create_material(texture: bpy.types.Texture, unique_id: str, idx: int) -> bpy.types.Material:
    """Create a Blender material using the atlas texture.

    Args:
        texture: Atlas texture.
        unique_id: Unique ID for the atlas.
        idx: Layer index for the material.

    Returns:
        Created Blender material.
    """
    mat = bpy.data.materials.new(name='{}{}_{}'.format(atlas_material_prefix, unique_id, idx))
    if is_blender_modern:
        _configure_material(mat, texture)
    else:
        _configure_material_legacy(mat, texture)
    return mat


def _configure_material(mat: bpy.types.Material, texture: bpy.types.Texture) -> None:
    """Configure a modern (Cycles/Eevee) material with the atlas texture.

    Args:
        mat: Material to configure.
        texture: Atlas texture.
    """
    mat.blend_method = 'CLIP'
    mat.use_backface_culling = True
    mat.use_nodes = True

    node_texture = mat.node_tree.nodes.new(type='ShaderNodeTexImage')
    node_texture.image = texture.image
    node_texture.label = 'Material Combiner Texture'
    node_texture.location = -300, 300

    node_bsdf = mat.node_tree.nodes['Principled BSDF']
    node_bsdf.inputs['Roughness'].default_value = 1

    mat.node_tree.links.new(node_texture.outputs['Color'], node_bsdf.inputs['Base Color'])
    mat.node_tree.links.new(node_texture.outputs['Alpha'], node_bsdf.inputs['Alpha'])


def _configure_material_legacy(mat: bpy.types.Material, texture: bpy.types.Texture) -> None:
    """Configure a legacy (Blender Internal) material with the atlas texture.

    Args:
        mat: Material to configure.
        texture: Atlas texture.
    """
    mat.alpha = 0
    mat.use_transparency = True
    mat.diffuse_color = (1, 1, 1)
    mat.use_shadeless = True

    tex = mat.texture_slots.add()
    tex.texture = texture
    tex.use_map_alpha = True


def assign_comb_mats(scn: Scene, data: SMCObData, comb_mats: CombMats) -> None:
    """Assign combined materials to objects.

    Args:
        scn: Current scene.
        data: Dictionary mapping object names to materials.
        comb_mats: Dictionary mapping layer indices to materials.
    """
    for ob_n, item in data.items():
        ob = scn.objects[ob_n]
        ob_materials = ob.data.materials
        _assign_mats(item, comb_mats, ob_materials)
        _assign_mats_to_polys(item, comb_mats, ob, ob_materials)


def _assign_mats(item: SMCObDataItem, comb_mats: CombMats, ob_materials: ObMats) -> None:
    """Add combined materials to an object's material slots.

    Args:
        item: Dictionary mapping materials to layer indices.
        comb_mats: Dictionary mapping layer indices to materials.
        ob_materials: Object's material collection.
    """
    for idx in set(item.values()):
        if idx in comb_mats:
            ob_materials.append(comb_mats[idx])


def _assign_mats_to_polys(item: SMCObDataItem, comb_mats: CombMats, ob: bpy.types.Object, ob_materials: ObMats) -> None:
    """Assign materials to polygons based on their layer.

    Args:
        item: Dictionary mapping materials to layer indices.
        comb_mats: Dictionary mapping layer indices to materials.
        ob: Object to assign materials to.
        ob_materials: Object's material collection.
    """
    for idx, polys in get_polys(ob).items():
        if ob_materials[idx] not in item:
            continue

        mat_name = comb_mats[item[ob_materials[idx]]].name
        mat_idx = ob_materials.find(mat_name)
        for poly in polys:
            poly.material_index = mat_idx


def clear_mats(scn: Scene, mats_uv: MatsUV) -> None:
    """Remove original materials from objects after a combination.

    Args:
        scn: Current scene.
        mats_uv: Dictionary mapping object names to materials with UV coordinates.
    """
    for ob_n, item in mats_uv.items():
        ob = scn.objects[ob_n]
        for mat in item:
            _delete_material(ob, mat.name)
