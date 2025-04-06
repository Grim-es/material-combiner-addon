import os
from typing import Optional

import bpy


def get_image(tex: bpy.types.Texture) -> Optional[bpy.types.Image]:
    return tex.image if tex and hasattr(tex, 'image') and tex.image else None


def get_packed_file(image: Optional[bpy.types.Image]) -> Optional[bpy.types.PackedFile]:
    if image and not image.packed_file and _get_image_path(image):
        image.pack()
    return image.packed_file if image and image.packed_file else None


def _get_image_path(img: Optional[bpy.types.Image]) -> Optional[str]:
    if not img:
        return None

    path = os.path.abspath(bpy.path.abspath(img.filepath))
    if os.path.isfile(path) and not path.lower().endswith(('.spa', '.sph')):
        return path
    return None
