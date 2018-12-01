import bpy
from . icons import get_icon_id


class CombLayersItems(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row()
        row.prop(item, 'layer', text='', emboss=False, icon_value=get_icon_id('broken_uv'))

    def invoke(self, context, event):
        pass


class ObDataItems(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row()
        if item.type == 0:
            row.label(item.ob.name, icon='VIEW3D')
            if item.used:
                used_text = 'Deselect All'
            else:
                used_text = 'Select All'
            row = row.row()
            row.alignment = 'RIGHT'
            row.operator('smc.combine_switch', text=used_text, emboss=False).list_id = index
        elif item.type == 1:
            row.separator()
            row = row.row(align=True)
            row.label(text='', icon_value=item.mat.preview.icon_id)
            row.prop(item, 'layer', text='{}'
                     .format(item.mat.name))
            if item.used:
                used_icon = 'FILE_TICK'
            else:
                used_icon = 'LAYER_USED'
            row.operator('smc.combine_switch', text='', icon=used_icon).list_id = index

    def invoke(self, context, event):
        pass
