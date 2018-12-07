import bpy
from .. icons import get_icon_id
try:
    from PIL import Image, ImageChops
    pil_exist = True
except ImportError:
    pil_exist = False


class MaterialMenu(bpy.types.Panel):
    bl_label = 'Main Menu'
    bl_idname = 'smc.main_menu'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = 'MatCombiner'

    def draw(self, context):
        scn = context.scene
        layout = self.layout
        col = layout.column()
        if scn.objects:
            if bpy.data.materials:
                if scn.smc_combine_state == 'COMB':
                    col = col.column(align=True)
                    box = col.box()
                    box.label('Select materials to combine:')
                    col.template_list('ObDataItems', 'combine_list', scn, 'smc_ob_data',
                                      scn, 'smc_ob_data_id', rows=12, type='DEFAULT')
                    col.operator('smc.refresh_ob_data', text='Refresh list', icon_value=get_icon_id('null'))
                    box = col.box()
                    box.label('Combine settings:')
                    box.prop(scn, 'smc_size')
                    if scn.smc_size == 'CUST':
                        box_col = box.column(align=True)
                        box_col.prop(scn, 'smc_size_width')
                        box_col.prop(scn, 'smc_size_height')
                    box.prop(scn, 'smc_compress', text='Compress combined image')
                    box.separator()
                    col = layout.column()
                    if pil_exist:
                        col.operator('smc.combiner', icon_value=get_icon_id('null'))
                        col.operator('smc.combine_menu_type', text='Multicombine',
                                     icon_value=get_icon_id('null')).state = 'MULT'
                    else:
                        col.label('Pillow was not found!', icon='ERROR')
                        col.label('Try to run Blender as Administrator.', icon_value=get_icon_id('null'))
                        col.label('or check your Internet Connection.', icon_value=get_icon_id('null'))
                        col.label('If error still occur, use options to', icon_value=get_icon_id('help'))
                        col.label('report on the "Credits" window.', icon_value=get_icon_id('null'))
                    col.operator('smc.combine_menu_type', text='Back', icon_value=get_icon_id('null')).state = 'MATS'
                elif scn.smc_combine_state == 'MULT':
                    box = col.box()
                    if scn.smc_multi_list:
                        box.template_icon_view(scn, 'smc_image_preview')
                        row = box.row()
                        img = bpy.data.images[scn.smc_image_preview]
                        row.template_list('ImageItems', 'img_name', img, 'smc_img_list',
                                          img, 'smc_img_list_id', rows=5, type='DEFAULT')
                        r_col = row.column(align=True)
                        r_col.operator('smc.img_add', text='', icon='ZOOMIN')
                        r_col.operator('smc.img_remove', text='', icon='ZOOMOUT')
                        r_col.separator()
                        r_col.operator('smc.img_move', icon='TRIA_UP', text='').type = 'UP'
                        r_col.operator('smc.img_move', icon='TRIA_DOWN', text='').type = 'DOWN'
                        col.operator('smc.combiner', icon_value=get_icon_id('null'))
                    else:
                        box.label('Selected materials to combine have no images')
                    col.operator('smc.combine_menu_type', text='Back', icon_value=get_icon_id('null')).state = 'COMB'
                else:
                    mat = bpy.data.materials[scn.smc_mats_preview]
                    box = col.box()
                    box.template_icon_view(scn, 'smc_mats_preview')
                    split = box.split(percentage=0.75, align=True)
                    split.prop(scn, 'smc_mats_preview', text='')
                    split.prop(mat, 'diffuse_color', text='')
                    box.prop(mat, 'smc_size')
                    if mat.smc_size:
                        box_col = box.column(align=True)
                        box_col.prop(mat, 'smc_size_width')
                        box_col.prop(mat, 'smc_size_height')
                    box.prop(mat, 'smc_diffuse')
                    col.operator('smc.combine_menu_type', text='Continue',
                                 icon_value=get_icon_id('null')).state = 'COMB'
            else:
                box = col.box()
                box.label('No materials found!', icon_value=get_icon_id('no_data'))
        else:
            box = col.box()
            box.label('No objects on the scene!', icon_value=get_icon_id('no_data'))
