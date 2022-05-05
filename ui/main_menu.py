import bpy
from .. import globs
from ..icons import get_icon_id


class MaterialMenu(bpy.types.Panel):
    bl_label = 'Main Menu'
    bl_idname = 'SMC_PT_Main_Menu'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI' if globs.version else 'TOOLS'
    bl_category = 'MatCombiner'

    def draw(self, context):
        scn = context.scene
        discord = 'https://discordapp.com/users/275608234595713024'
        layout = self.layout
        col = layout.column(align=True)
        col.label(text='Materials to combine:')
        col.template_list('SMC_UL_Combine_List', 'combine_list', scn, 'smc_ob_data',
                          scn, 'smc_ob_data_id', rows=12, type='DEFAULT')
        col = col.column(align=True)
        col.scale_y = 1.2
        col.operator('smc.refresh_ob_data',
                     text='Update Material List' if scn.smc_ob_data else 'Generate Material List',
                     icon_value=get_icon_id('null'))
        col = layout.column()
        col.label(text='Properties:')
        box = col.box()
        box.scale_y = 1.2
        box.prop(scn, 'smc_size')
        if scn.smc_size == 'CUST':
            box.prop(scn, 'smc_size_width')
            box.prop(scn, 'smc_size_height')
        box.scale_y = 1.2
        box.prop(scn, 'smc_crop')
        row = box.row()
        col = row.column()
        col.scale_y = 1.2
        col.label(text='Size of materials without image')
        col = row.column()
        col.scale_x = .75
        col.scale_y = 1.2
        col.alignment = 'RIGHT'
        col.prop(scn, 'smc_diffuse_size', text='')
        row = box.row()
        col = row.column()
        col.scale_y = 1.2
        col.label(text='Size of gaps between images')
        col = row.column()
        col.scale_x = .75
        col.scale_y = 1.2
        col.alignment = 'RIGHT'
        col.prop(scn, 'smc_gaps', text='')
        col = box.column()
        col.label(text='Multicombining currently disabled', icon_value=get_icon_id('info'))
        col = layout.column()
        col.scale_y = 1.5
        col.operator('smc.combiner', text='Save Atlas to..', icon_value=get_icon_id('null')).cats = False
