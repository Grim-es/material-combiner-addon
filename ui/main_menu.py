import bpy
from .. icons import get_icon_id
from .. import globs


class MaterialMenu(bpy.types.Panel):
    bl_label = 'Main Menu'
    bl_idname = 'SMC_PT_Main_Menu'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS' if bpy.app.version < (2, 80) else 'UI'
    bl_category = 'MatCombiner'

    def draw(self, context):
        scn = context.scene
        manual = 'https://vrcat.club/threads/material-combiner-blender-addon-2-0-3-2.2255/page-3#post-9712'
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
            col.operator('smc.combiner', text='Save Atlas to..', icon_value=get_icon_id('null'))
        else:
            if globs.smc_pi:
                col = col.box().column()
                col.label(text='Installation complete', icon_value=get_icon_id('done'))
                col.label(text='Please restart Blender', icon_value=get_icon_id('null'))
            else:
                col.label(text='Python Imaging Library required to continue')
                col.separator()
                row = col.row()
                row.scale_y = 1.5
                row.operator('smc.get_pillow', text='Install Pillow', icon_value=get_icon_id('download'))
                col.separator()
                col.separator()
                col = col.box().column()
                col.label(text='If the installation process is repeated')
                col.label(text='try to run Blender as Administrator')
                col.label(text='or check your Internet Connection.')
                col.separator()
                col.label(text='If the error persists, try installing manually:')
                col.operator('smc.browser', text='Manual Install', icon_value=get_icon_id('help')).link = manual
