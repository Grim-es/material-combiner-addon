import bpy
import os


def tex_path(tex):
    path = bpy.path.abspath(tex.image.filepath) if tex and tex.image else ''
    return path if os.path.isfile(path) else ''
