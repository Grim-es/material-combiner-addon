import os

import bpy


def get_image(tex: bpy.types.Texture) -> bpy.types.Image:
    return tex.image if tex and hasattr(tex, 'image') and tex.image else None


def get_image_path(image: bpy.types.Image) -> str:
    path = bpy.path.abspath(image.filepath) if image else ''
    return path if os.path.isfile(path) and not path.lower().endswith(('.spa', '.sph')) else ''
