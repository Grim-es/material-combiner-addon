import bpy
import os
from bpy.props import *
from subprocess import call
from .. icons import get_icon_id


class OpenBrowser(bpy.types.Operator):
    bl_idname = 'smc.compress'
    bl_label = 'Compress all textures'

    def show_message(self, context):
        def draw(self, context):
            layout = self.layout
            col = layout.column()
            col.operator('smc.zip_download', icon_value=get_icon_id('null')
                         ).link = 'https://pngquant.org/pngquant-windows.zip'
        context.window_manager.popup_menu(draw, title='Pngquant is not installed', icon='INFO')

    def execute(self, context):
        scn = context.scene
        pngquant = os.path.abspath(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, 'assets', 'pngquant', 'pngquant.exe'))
        if os.path.isfile(os.path.join(pngquant)):
            command = '"{}" -f --ext .png --skip-if-larger -v "{}"'.format(pngquant, scn.smc_save_path)
            call(command, shell=True)
            self.report({'INFO'}, 'Files compressed')
        else:
            self.show_message(context)
        return {'FINISHED'}
