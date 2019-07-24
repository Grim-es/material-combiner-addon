import bpy
from .. import addon_updater_ops


class UpdateMenu(bpy.types.Panel):
    bl_label = 'Updates'
    bl_idname = 'SMC_PT_Update_Menu'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS' if bpy.app.version < (2, 80) else 'UI'
    bl_category = 'MatCombiner'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        addon_updater_ops.update_settings_ui(self, context)
