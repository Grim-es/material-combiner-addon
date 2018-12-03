import bpy
import os


def tex_img(tex):
    return tex.image if tex and tex.image else ''


def tex_path(img):
    path = bpy.path.abspath(img.filepath)
    return path if os.path.isfile(path) else ''
