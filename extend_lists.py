import bpy
from . import globs


class SMC_UL_Combine_List(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        if item.type == 0:
            row.prop(item.ob, 'name', text='', icon='META_CUBE' if globs.version else 'VIEW3D', emboss=False)
            row = row.row()
            row.alignment = 'RIGHT'
            row.operator('smc.combine_switch',
                         text='Deselect All' if item.used else 'Select All',
                         emboss=False).list_id = index
        elif item.type == 1:
            row.separator()
            row.label(text='', icon_value=item.mat.preview.icon_id)
            row.prop(item.mat, 'name', text='')
            col = row.column(align=True)
            col.alignment = 'RIGHT'
            col.scale_x = .6
            col.prop(item, 'layer', text='')
            if item.used:
                icon = 'CHECKBOX_HLT' if globs.version else 'FILE_TICK'
            else:
                icon = 'CHECKBOX_DEHLT' if globs.version else 'LAYER_USED'
            row.operator('smc.combine_switch', text='', icon=icon).list_id = index
            row.operator('smc.properties_menu', text='',
                         icon='PREFERENCES' if globs.version else 'SCRIPT').list_id = index

    def invoke(self, context, event):
        pass
