import bpy

from .. import bl_info, globs
from ..icons import get_icon_id

DISCORD_URL = 'https://discordapp.com/users/275608234595713024'
GITHUB_ISSUES_URL = 'https://github.com/Grim-es/material-combiner-addon/issues'
PATREON_URL = 'https://www.patreon.com/shotariya'
BUYMEACOFFEE_URL = 'https://buymeacoffee.com/shotariya'


class CreditsMenu(bpy.types.Panel):
    bl_label = 'Credits & Support'
    bl_idname = 'SMC_PT_Credits_Menu'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI' if globs.is_blender_2_80_or_newer else 'TOOLS'
    bl_category = 'MatCombiner'

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        self._draw_header_section(layout)
        self._draw_contact_section(layout)
        self._draw_support_section(layout)

    @staticmethod
    def _draw_header_section(layout: bpy.types.UILayout) -> None:
        box = layout.box()
        col = box.column()
        col.scale_y = 1.2

        version_str = '.'.join(map(str, bl_info['version']))
        col.label(
            text='Material Combiner {0}'.format(version_str),
            icon_value=get_icon_id('smc')
        )

        author_row = box.row(align=True)
        author_row.scale_y = 1.2
        author_row.alignment = 'LEFT'
        author_row.label(text='Created by:')
        author_row.label(text='shotariya', icon_value=get_icon_id('shot'))

    def _draw_contact_section(self, layout: bpy.types.UILayout) -> None:
        box = layout.box()
        col = box.column(align=True)
        col.scale_y = 1.2

        col.label(text='Found an Issue?')
        self._create_link_button(
            col,
            text='Contact on Discord (@shotariya)',
            icon='discord',
            url=DISCORD_URL
        )
        self._create_link_button(
            col,
            text='Report Bug on GitHub',
            icon='github',
            url=GITHUB_ISSUES_URL
        )

    def _draw_support_section(self, layout: bpy.types.UILayout) -> None:
        box = layout.box()
        col = box.column(align=True)
        col.scale_y = 1.2

        col.label(text='Support Development:')
        self._create_link_button(
            col,
            text='Patreon Support',
            icon='patreon',
            url=PATREON_URL
        )
        self._create_link_button(
            col,
            text='Buy Me a Coffee',
            icon='bmc',
            url=BUYMEACOFFEE_URL
        )

    @staticmethod
    def _create_link_button(layout: bpy.types.UILayout, text: str, icon: str, url: str) -> None:
        layout.operator(
            'smc.browser',
            text=text,
            icon_value=get_icon_id(icon)
        ).link = url
