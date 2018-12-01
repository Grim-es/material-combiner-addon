import bpy
from .. icons import get_icon_id
from .. import addon_updater_ops


class UpdateMenu(bpy.types.Panel):
    bl_label = 'Updates'
    bl_idname = 'smc.update_menu'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = 'Material Combiner'

    def draw(self, context):
        addon_updater_ops.update_settings_ui(self, context)
