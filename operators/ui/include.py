import bpy
from ... icons import get_icon_id
try:
    import PIL
    pil_exist = True
except ImportError:
    pil_exist = False


def draw_ui(context, m_col):
    scn = context.scene
    vrcat = 'https://vrcat.club/threads/material-combiner-blender-addon.2255'
    discord = 'https://discordapp.com/users/275608234595713024'
    if scn.smc_ob_data:
        m_col.template_list('ObDataItems', 'combine_list', scn, 'smc_ob_data',
                            scn, 'smc_ob_data_id', rows=12, type='DEFAULT')
        state_text = 'Update Material List'
    else:
        state_text = 'Generate Material List'
    if scn.objects:
        if bpy.data.materials:
            col = m_col.column(align=True)
            col.scale_y = 1.2
            col.operator('smc.refresh_ob_data', text=state_text, icon_value=get_icon_id('null'))
            m_col.separator()
            if pil_exist:
                col = m_col.column()
                col.scale_y = 1.5
                col.operator('smc.combiner', text='Save Atlas to..', icon_value=get_icon_id('null'))
            else:
                box = m_col.box()
                col = box.column(align=True)
                col.label('Pillow was not found!', icon='ERROR')
                col.label('Try to run Blender as administrator', icon_value=get_icon_id('null'))
                col.label('or check your Internet Connection', icon_value=get_icon_id('null'))
                col.label('and restart Blender', icon_value=get_icon_id('null'))
                col.separator()
                col.label('If error still occur:', icon_value=get_icon_id('report'))
                col = box.column(align=True)
                col.scale_y = 1.2
                col.operator('smc.browser', text='Post it on forum (VRcat.club)', icon_value=get_icon_id('vrcat')).link = vrcat
                col.operator('smc.browser', text='Contact me on Discord', icon_value=get_icon_id('discord')).link = discord
        else:
            box = m_col.box()
            box.label(text='No materials found!', icon='ERROR')
    else:
        box = m_col.box()
        box.label(text='No meshes found!', icon='ERROR')
