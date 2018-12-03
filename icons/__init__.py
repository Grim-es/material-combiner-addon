import bpy
import os
import bpy.utils.previews

smc_icons = None
icons_directory = os.path.dirname(__file__)


def get_icon_id(identifier):
    return get_icon(identifier).icon_id


def get_icon(identifier):
    if identifier in smc_icons:
        return smc_icons[identifier]
    return smc_icons.load(identifier, os.path.join(icons_directory, identifier + '.png'), 'IMAGE')


def get_img_icon_id(identifier, path):
    return get_img_icon(identifier, path).icon_id


def get_img_icon(identifier, path):
    if identifier in smc_icons:
        return smc_icons[identifier]
    return smc_icons.load(identifier, path, 'IMAGE')


def initialize_smc_icons():
    global smc_icons
    smc_icons = bpy.utils.previews.new()


def unload_smc_icons():
    bpy.utils.previews.remove(smc_icons)
