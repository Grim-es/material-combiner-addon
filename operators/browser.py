import bpy
import webbrowser
from bpy.props import *


class OpenBrowser(bpy.types.Operator):
    bl_idname = 'smc.browser'
    bl_label = 'Open Browser'

    link = StringProperty(default='')

    def execute(self, context):
        webbrowser.open(self.link)
        self.report({'INFO'}, 'Browser opened')
        return {'FINISHED'}
