from ... import globs
from ...icons import get_icon_id


def draw_ui(context, m_col):
    scn = context.scene
    patreon = 'https://www.patreon.com/shotariya'
    discord = 'https://discordapp.com/users/275608234595713024'
    if globs.pil_exist:
        if scn.smc_ob_data:
            m_col.template_list('SMC_UL_Combine_List', 'combine_list', scn, 'smc_ob_data',
                                scn, 'smc_ob_data_id', rows=12, type='DEFAULT')
        col = m_col.column(align=True)
        col.scale_y = 1.2
        col.operator('smc.refresh_ob_data',
                     text='Update Material List' if scn.smc_ob_data else 'Generate Material List',
                     icon_value=get_icon_id('null'))
        col = m_col.column()
        col.scale_y = 1.5
        col.operator('smc.combiner', text='Save Atlas to..', icon_value=get_icon_id('null')).cats = True
        col.separator()
        col = m_col.column()
        col.label(text='If this saved you time:')
        col.operator('smc.browser', text='Support Material Combiner', icon_value=get_icon_id('patreon')).link = patreon
    else:
        if globs.smc_pi:
            col = m_col.box().column()
            col.label(text='Installation complete', icon_value=get_icon_id('done'))
            col.label(text='Please restart Blender', icon_value=get_icon_id('null'))
        else:
            col = m_col.box().column()
            col.label(text='Dependencies (Pillow and Z3) required to continue')
            col.separator()
            row = col.row()
            row.scale_y = 1.5
            row.operator('smc.get_pillow', text='Install Dependencies', icon_value=get_icon_id('download'))
            col.separator()
            col.separator()
            col.label(text='If the installation process is repeated')
            col.label(text='try to run Blender as Administrator')
            col.label(text='or check your Internet Connection.')
            col.separator()
            col.label(text='If the error persists, contact me on Discord for a manual installation:')
            col.operator('smc.browser', text='shotariya#4269', icon_value=get_icon_id('help')).link = discord
