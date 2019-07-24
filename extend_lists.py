import bpy


class SMC_UL_Combine_List(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row()
        if item.type == 0:
            row.label(text=item.ob.name, icon='META_CUBE' if bpy.app.version >= (2, 80, 0) else 'VIEW3D')
            row = row.row()
            row.alignment = 'RIGHT'
            row.operator('smc.combine_switch',
                         text='Deselect All' if item.used else 'Select All',
                         emboss=False).list_id = index
        elif item.type == 1:
            row.separator()
            row = row.row(align=True)
            row.label(text='', icon_value=item.mat.preview.icon_id)
            row.prop(item, 'layer', text=item.mat.name)
            row.operator('smc.combine_switch', text='', icon=(
                'CHECKBOX_HLT' if item.used else 'CHECKBOX_DEHLT') if bpy.app.version >= (2, 80, 0) else (
                'FILE_TICK' if item.used else 'LAYER_USED')).list_id = index
            row.operator('smc.properties_menu', text='',
                         icon='PREFERENCES' if bpy.app.version >= (2, 80, 0) else 'SCRIPT').list_id = index

    def invoke(self, context, event):
        pass
