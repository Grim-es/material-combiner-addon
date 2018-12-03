import bpy
from .. import addon_updater_ops


class UpdateMenu(bpy.types.Panel):
    bl_label = 'Updates'
    bl_idname = 'smc.update_menu'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = 'Material Combiner'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        addon_updater_ops.update_settings_ui(self, context)
