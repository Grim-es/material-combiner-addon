import bpy
from bpy.props import *
from bpy.app.handlers import persistent
from . import extend_types
from . icons import initialize_smc_icons, unload_smc_icons
from . import addon_updater_ops


@persistent
def saved_folder(dummy):
    scn = bpy.context.scene
    if not scn.smc_save_path and bpy.path.abspath('//'):
        scn.smc_save_path = bpy.path.abspath('//')


def register_all():
    initialize_smc_icons()
    addon_updater_ops.register()
    extend_types.register()
    if saved_folder not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(saved_folder)
    if saved_folder not in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.append(saved_folder)
    if saved_folder not in bpy.app.handlers.scene_update_post:
        bpy.app.handlers.scene_update_post.append(saved_folder)


def unregister_all():
    unload_smc_icons()
    addon_updater_ops.unregister()
    extend_types.unregister()
    if saved_folder in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(saved_folder)
    if saved_folder in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.remove(saved_folder)
    if saved_folder in bpy.app.handlers.scene_update_post:
        bpy.app.handlers.scene_update_post.remove(saved_folder)
