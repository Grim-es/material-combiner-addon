from typing import Dict

import bpy


def get_texture(mat: bpy.types.Material) -> bpy.types.Texture:
    return next((slot.texture for idx, slot in enumerate(mat.texture_slots) if
                 slot is not None and mat.use_textures[idx]), None)


def get_textures(mat: bpy.types.Material) -> Dict[int, bpy.types.Texture]:
    return {idx: slot.texture for idx, slot in enumerate(mat.texture_slots) if
            slot is not None and mat.use_textures[idx]}
