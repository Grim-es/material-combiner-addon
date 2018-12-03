import bpy
from .. import bl_info
from .. icons import get_icon_id


class CreditsMenu(bpy.types.Panel):
    bl_label = 'Credits'
    bl_idname = 'smc.credits_menu'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = 'Material Combiner'

    def draw(self, context):
        vrcat = 'https://vrcat.club/threads/material-combiner-blender-addon.2255'
        discord = 'https://discordapp.com/users/275608234595713024'
        layout = self.layout
        m_col = layout.column()
        box = m_col.box()
        col = box.column(align=True)
        col.label('Material Combiner ({})'.format(bl_info['version']), icon_value=get_icon_id('smc'))
        col.separator()
        col.label('Author: shotariya')
        col.separator()
        col.label('If you have found a bug:')
        col.operator('smc.browser', text='Post it on forum (VRcat.club)', icon_value=get_icon_id('vrcat')).link = vrcat
        col.operator('smc.browser', text='Contact me on Discord', icon_value=get_icon_id('discord')).link = discord
        col.separator()
