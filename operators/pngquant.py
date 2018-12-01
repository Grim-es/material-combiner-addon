import bpy
import os
from bpy.props import *
from subprocess import call


class OpenBrowser(bpy.types.Operator):
    bl_idname = 'smc.compress'
    bl_label = 'Compress all textures'

    def execute(self, context):
        scn = context.scene
        pngquant = os.path.abspath(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, 'assets', 'pngquant', 'pngquant.exe'))
        if not os.path.isfile(os.path.join(pngquant)):
            bpy.ops.smc.zip_download(link='https://pngquant.org/pngquant-windows.zip')
        command = '"{}" -f --ext .png --skip-if-larger -v "{}"'.format(pngquant, scn.smc_save_path)
        call(command, shell=True)
        self.report({'INFO'}, 'Files compressed')

        return {'FINISHED'}
