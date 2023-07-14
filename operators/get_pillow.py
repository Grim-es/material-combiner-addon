import subprocess
import sys
from typing import Set

import bpy

from .. import globs


class InstallPIL(bpy.types.Operator):
    bl_idname = 'smc.get_pillow'
    bl_label = 'Install PIL'
    bl_description = 'Click to install Pillow. This could take a while and might require you to run Blender as Admin.'

    def execute(self, context: bpy.types.Context) -> Set[str]:
        try:
            import pip
            try:
                from PIL import Image, ImageChops
            except ImportError:
                self._install_pillow()
        except ImportError:
            self._install_pip()
            self._install_pillow()

        globs.smc_pi = True

        self.report({'INFO'}, 'Installation complete')
        return {'FINISHED'}

    @staticmethod
    def _install_pip() -> None:
        if globs.is_blender_2_80_or_newer:
            import ensurepip
            ensurepip.bootstrap()
        else:
            python_executable = sys.executable if globs.is_blender_2_92_or_newer else bpy.app.binary_path_python
            subprocess.call([python_executable, 'get-pip.py'], shell=True)

    @staticmethod
    def _install_pillow() -> None:
        from pip import _internal
        _internal.main(['install', 'pip', 'setuptools', 'wheel', '-U'])
        _internal.main(['install', 'Pillow'])
