from typing import Optional

import bpy


def get_texture(mat: bpy.types.Material) -> Optional[bpy.types.Texture]:
    if not hasattr(mat, 'texture_slots') or not mat.texture_slots:
        return None

    return next(
        (slot.texture for idx, slot in enumerate(mat.texture_slots) if mat.use_textures[idx]),
        None
    )
