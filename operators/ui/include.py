from ... import globs
from ...icons import get_icon_id


def draw_ui(context, m_col):
    scn = context.scene
    patreon = 'https://www.patreon.com/shotariya'
    # TODO: Now unsused
    discord = 'https://discordapp.com/users/275608234595713024'
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
