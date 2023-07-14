import bpy

from .. import globs
from ..icons import get_icon_id
from ..type_annotations import Scene


class MaterialMenu(bpy.types.Panel):
    bl_label = 'Main Menu'
    bl_idname = 'SMC_PT_Main_Menu'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI' if globs.is_blender_2_80_or_newer else 'TOOLS'
    bl_category = 'MatCombiner'

    def draw(self, context: bpy.types.Context) -> None:
        scn = context.scene
        layout = self.layout
        col = layout.column(align=True)
        if globs.pil_exist:
            self._materials_list(col, scn, layout)
        elif globs.smc_pi:
            col = col.box().column()
            col.label(text='Installation complete', icon_value=get_icon_id('done'))
            col.label(text='Please restart Blender', icon_value=get_icon_id('null'))
        else:
            self.pillow_installator(col)

    @staticmethod
    def _materials_list(col: bpy.types.UILayout, scn: Scene, layout: bpy.types.UIList) -> None:
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
        if scn.smc_size in ['CUST', 'STRICTCUST']:
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
        col = layout.column()
        col.scale_y = 1.5
        col.operator('smc.combiner', text='Save Atlas to..', icon_value=get_icon_id('null')).cats = False

    @staticmethod
    def pillow_installator(col: bpy.types.UILayout) -> None:
        discord = 'https://discordapp.com/users/275608234595713024'

        col.label(text='Python Imaging Library required to continue')
        col.separator()
        row = col.row()
        row.scale_y = 1.5
        row.operator('smc.get_pillow', text='Install Pillow', icon_value=get_icon_id('download'))
        col.separator()
        col.separator()
        col = col.box().column()
        col.label(text='If the installation process is repeated'
                       '\ntry to run Blender as Administrator'
                       '\nor check your Internet Connection.')
        col.separator()
        col.label(text='If the error persists, contact me on Discord for a manual installation:')
        col.operator('smc.browser', text='shotariya#4269', icon_value=get_icon_id('help')).link = discord
