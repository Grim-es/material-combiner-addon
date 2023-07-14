import webbrowser
from typing import Set

import bpy
from bpy.props import *


class OpenBrowser(bpy.types.Operator):
    bl_idname = 'smc.browser'
    bl_label = 'Open Browser'
    bl_description = 'Click to open in browser'

    link = StringProperty(default='')

    def execute(self, context: bpy.types.Context) -> Set[str]:
        webbrowser.open(self.link)
        self.report({'INFO'}, 'Browser opened')
        return {'FINISHED'}
