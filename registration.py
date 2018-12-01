import bpy
from bpy.props import *
from . import extend_types
from . icons import initialize_smc_icons, unload_smc_icons
from . import addon_updater_ops


def register_all():
    initialize_smc_icons()
    addon_updater_ops.register()
    extend_types.register()


def unregister_all():
    unload_smc_icons()
    addon_updater_ops.unregister()
    extend_types.unregister()
