from ... import globs
from ...icons import get_icon_id


def draw_ui(context, m_col):
    scn = context.scene
    manual = 'https://vrcat.club/threads/material-combiner-blender-addon-2-0-3-2.2255/page-3#post-9712'
    patreon = 'https://www.patreon.com/shotariya'
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
            col.label(text='Python Imaging Library required to continue')
            col.separator()
            row = col.row()
            row.scale_y = 1.5
            row.operator('smc.get_pillow', text='Install Pillow', icon_value=get_icon_id('download'))
            col.separator()
            col.separator()
            col.label(text='If the installation process is repeated')
            col.label(text='try to run Blender as Administrator')
            col.label(text='or check your Internet Connection.')
            col.separator()
            col.label(text='If the error persists, try installing manually:')
            col.operator('smc.browser', text='Manual Install', icon_value=get_icon_id('help')).link = manual
