import bpy
from .. icons import get_icon_id
try:
    import PIL
    pil_exist = True
except ImportError:
    pil_exist = True


class MaterialMenu(bpy.types.Panel):
    bl_label = 'Main Menu'
    bl_idname = 'smc.main_menu'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = 'Material Combiner'

    def draw(self, context):
        scn = context.scene
        layout = self.layout
        col = layout.column()
        if scn.objects:
            if bpy.data.materials:
                if scn.smc_combine_state:
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
                    box.prop(scn, 'smc_mat_slots', text='Multicombining (Currently disabled)')
                    if scn.smc_mat_slots:
                        tex = mat.active_texture
                        box.template_list('TEXTURE_UL_texslots', '', mat, 'texture_slots',
                                          mat, 'active_texture_index', rows=2)
                        box.template_ID(mat, 'active_texture', new='texture.new')
                        if mat.active_texture:
                            if mat.active_texture.image:
                                box.label('Image: size {} x {}'.format(tex.image.size[0], tex.image.size[1]))
                                row = box.row(align=True)
                                row.prop(tex.image, 'filepath', text='')
                                row.operator('image.reload', text='', icon='FILE_REFRESH')
                    col.operator('smc.combine_menu_type', text='Continue', icon_value=get_icon_id('null'))
                else:
                    col = col.column(align=True)
                    box = col.box()
                    box.label('Select materials to combine:')
                    col.template_list('ObDataItems', 'combine_list', scn, 'smc_ob_data',
                                      scn, 'smc_ob_data_id', rows=12, type='DEFAULT')
                    box = col.box()
                    box.label('Combine settings:')
                    box.prop(scn, 'smc_size')
                    if scn.smc_size == 'CUST':
                        box_col = box.column(align=True)
                        box_col.prop(scn, 'smc_size_width')
                        box_col.prop(scn, 'smc_size_height')
                    box.prop(scn, 'smc_compress', text='Compress combined image')
                    col = layout.column()
                    if pil_exist:
                        col.operator('smc.combiner', icon_value=get_icon_id('null'))
                    else:
                        col.label('Pillow is not installed, please', icon='ERROR')
                        col.label('check your internet connection.', icon_value=get_icon_id('null'))
                        col.label('If error still occur, use options to', icon_value=get_icon_id('help'))
                        col.label('report on the "Credits" window.', icon_value=get_icon_id('null'))
                    col.operator('smc.combine_menu_type', text='Back', icon_value=get_icon_id('null'))
            else:
                col.label('No materials found.', icon_value=get_icon_id('no_data'))
        else:
            col.label('No objects on the scene.', icon_value=get_icon_id('no_data'))
