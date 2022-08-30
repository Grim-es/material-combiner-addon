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
        if globs.pil_exist:
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
            box.scale_y = 1.0
            box.prop(scn, 'smc_use_advanced_packer')
            row = box.row()
            col = row.column()
            col.label(text=bpy.types.Scene.smc_advanced_packing_round_time_limit[1]["name"])
            col = row.column()
            col.scale_x = .75
            col.scale_y = 1.0
            col.alignment = 'RIGHT'
            col.prop(scn, 'smc_advanced_packing_round_time_limit', text='')
            if scn.smc_use_advanced_packer:
                col.enabled = True
            else:
                col.enabled = False
            box.prop(scn, 'smc_crop')
            row = box.row()
            col = row.column()
            col.scale_y = 1.0
            col.label(text='Size of materials without image')
            col = row.column()
            col.scale_x = .75
            col.scale_y = 1.0
            col.alignment = 'RIGHT'
            col.prop(scn, 'smc_diffuse_size', text='')
            row = box.row()
            col = row.column()
            col.scale_y = 1.0
            col.label(text='Size of gaps between images')
            col = row.column()
            col.scale_x = .75
            col.scale_y = 1.0
            col.alignment = 'RIGHT'
            col.prop(scn, 'smc_gaps', text='')
            col = box.column()
            col.label(text='Multicombining currently disabled', icon_value=get_icon_id('info'))
            col = layout.column()
            col.scale_y = 1.5
            col.operator('smc.combiner', text='Save Atlas to..', icon_value=get_icon_id('null')).cats = False
        else:
            if globs.smc_pi:
                col = col.box().column()
                col.label(text='Installation complete', icon_value=get_icon_id('done'))
                col.label(text='Please restart Blender', icon_value=get_icon_id('null'))
            else:
                col.label(text='Dependencies (Pillow and Z3) required to continue')
                col.separator()
                row = col.row()
                row.scale_y = 1.5
                row.operator('smc.get_pillow', text='Install Dependencies', icon_value=get_icon_id('download'))
                col.separator()
                col.separator()
                col = col.box().column()
                col.label(text='If the installation process is repeated')
                col.label(text='try to run Blender as Administrator')
                col.label(text='or check your Internet Connection.')
                col.separator()
                col.label(text='If the error persists, contact me on Discord for a manual installation:')
                col.operator('smc.browser', text='shotariya#4269', icon_value=get_icon_id('help')).link = discord
