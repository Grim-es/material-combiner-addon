"""Image handling utilities for Material Combiner.

This module provides functions for retrieving and managing images associated
with Blender textures and materials, including handling packed and unpacked images.
"""

import os
from typing import Optional

import bpy


def get_image(tex: bpy.types.Texture) -> Optional[bpy.types.Image]:
    """Extract image from a Blender texture.

    Args:
        tex: Blender texture object to extract image from.

    Returns:
        The image associated with the texture or None if not found.
    """
    return tex.image if tex and hasattr(tex, "image") and tex.image else None


def get_packed_file(
    image: Optional[bpy.types.Image],
) -> Optional[bpy.types.PackedFile]:
    """Get packed file data from an image, packing if necessary.

    If the image exists but is not packed, this function attempts to pack it.

    Args:
        image: Blender image to get packed data from.

    Returns:
        The image's packed file data or None if unavailable.
    """
    if image and not image.packed_file and _get_image_path(image):
        image.pack()
    return image.packed_file if image and image.packed_file else None


def _get_image_path(img: Optional[bpy.types.Image]) -> Optional[str]:
    """Get the absolute file path for an image.

    Resolves the absolute path and filters out unsupported special formats.

    Args:
        img: Blender image to get the path for.

    Returns:
        Absolute file path if valid, None otherwise.
    """
    if not img:
        return None

    path = os.path.abspath(bpy.path.abspath(img.filepath))
    if os.path.isfile(path) and not path.lower().endswith((".spa", ".sph")):
        return path
    return None
