import os
from subprocess import call

import bpy
from .. import globs


class InstallPIL(bpy.types.Operator):
    bl_idname = 'smc.get_pillow'
    bl_label = 'Install PIL'

    def execute(self, context):
        try:
            import pip
            try:
                from PIL import Image, ImageChops
            except ImportError:
                call([bpy.app.binary_path_python, '-m', 'pip', 'install', 'Pillow', '--user', '--upgrade'], shell=True)
        except ImportError:
            call([bpy.app.binary_path_python, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'get_pip.py'),
                  '--user'], shell=True)
            call([bpy.app.binary_path_python, '-m', 'pip', 'install', 'Pillow', '--user', '--upgrade'], shell=True)
        globs.smc_pi = True
        self.report({'INFO'}, 'Installation complete')
        return {'FINISHED'}
