import os

import bpy


def get_image(tex):
    return tex.image if tex and hasattr(tex, 'image') and tex.image else None


def get_image_path(img):
    path = bpy.path.abspath(img.filepath) if img else ''
    return path if os.path.isfile(path) and not path.lower().endswith(('.spa', '.sph')) else ''
