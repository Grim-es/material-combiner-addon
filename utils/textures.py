"""Texture handling utilities for Material Combiner.

This module provides functions for retrieving texture information
from materials, specifically focusing on Blender Internal textures
for backward compatibility with older Blender versions.
"""

from typing import Optional

import bpy


def get_texture(mat: bpy.types.Material) -> Optional[bpy.types.Texture]:
    """Get the first enabled texture from a material's texture slots.

    This function works with Blender Internal materials (pre-2.80)
    that use texture slots.

    Args:
        mat: Material to extract texture from

    Returns:
        First enabled texture from the material or None if not found
    """
    if not hasattr(mat, "texture_slots") or not mat.texture_slots:
        return None

    return next(
        (
            slot.texture
            for idx, slot in enumerate(mat.texture_slots)
            if mat.use_textures[idx]
        ),
        None,
    )
