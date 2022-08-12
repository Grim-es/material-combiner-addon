import bpy
from . import globs
from .utils.previews import get_preview


class SMC_UL_Combine_List(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        if item.type == globs.C_L_OBJECT:
            row.prop(item.ob, 'name', text='', icon='META_CUBE' if globs.is_blender_2_80_or_newer else 'VIEW3D', emboss=False)
            row = row.row()
            row.alignment = 'RIGHT'
            row.operator('smc.combine_switch',
                         text='Deselect All' if item.used else 'Select All',
                         emboss=False).list_id = index
        elif item.type == globs.C_L_MATERIAL:
            row.separator()
            row.label(text='', icon_value=get_preview(item.mat).icon_id)
            row.prop(item.mat, 'name', text='')
            col = row.column(align=True)
            col.alignment = 'RIGHT'
            col.scale_x = .6
            col.prop(item, 'layer', text='')
            if item.used:
                icon = 'CHECKBOX_HLT' if globs.is_blender_2_80_or_newer else 'FILE_TICK'
            else:
                icon = 'CHECKBOX_DEHLT' if globs.is_blender_2_80_or_newer else 'LAYER_USED'
            row.operator('smc.combine_switch', text='', icon=icon).list_id = index
            row.operator('smc.properties_menu', text='',
                         icon='PREFERENCES' if globs.is_blender_2_80_or_newer else 'SCRIPT').list_id = index

    def invoke(self, context, event):
        pass

    def filter_items(self, context, data, propname):
        col = getattr(data, propname)
        filter_name = self.filter_name.lower()
        flt_flags = [self.bitflag_filter_item if item.type == globs.C_L_MATERIAL and filter_name in item.mat.name.lower() or
                     item.type == globs.C_L_OBJECT else 0 for i, item in enumerate(col, 1)]
        if self.use_filter_sort_alpha:
            flt_neworder = [x[1] for x in sorted(zip([x[0] for x in sorted(
                enumerate(col), key=lambda x: x[1].mat.name if x[1].type == globs.C_L_MATERIAL else '')], range(len(col))))]
        else:
            flt_neworder = []
        return flt_flags, flt_neworder
