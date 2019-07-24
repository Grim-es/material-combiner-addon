import bpy
import os


def get_image(tex):
    return tex.image if tex and tex.image else None


def get_image_path(img):
    path = bpy.path.abspath(img.filepath) if img else ''
    return path if os.path.isfile(path) else ''
