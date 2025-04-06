import importlib
import os
import subprocess
import sys
from typing import Set

import bpy

from .. import globs


class InstallPIL(bpy.types.Operator):
    bl_idname = "smc.get_pillow"
    bl_label = "Install PIL"
    bl_description = "Click to install Pillow. This could take a while and might require you to run Blender as Admin."

    def execute(self, context: bpy.types.Context) -> Set[str]:
        pip_exists = importlib.util.find_spec('pip._internal') is not None
        pil_exists = all(
            importlib.util.find_spec(m) is not None
            for m in ('PIL', 'PIL.Image', 'PIL.ImageChops')
        )

        if not pip_exists:
            self._install_pip()
            self._install_pillow()
        elif not pil_exists:
            self._install_pillow()

        globs.smc_pi = True

        self.report({"INFO"}, "Installation complete")
        return {"FINISHED"}

    def _install_pip(self) -> None:
        if globs.is_blender_2_80_or_newer:
            try:
                import ensurepip

                ensurepip.bootstrap()
            except ImportError:
                self._install_pip_clean()
        else:
            self._install_pip_clean()

    @staticmethod
    def _install_pip_clean() -> None:
        python_executable = (
            sys.executable
            if globs.is_blender_2_92_or_newer
            else bpy.app.binary_path_python
        )
        get_pip = os.path.join(os.path.dirname(os.path.abspath(__file__)), "get-pip.py")
        subprocess.call(
            [python_executable, get_pip, "--user", "--force-reinstall"], shell=True
        )

    @staticmethod
    def _install_pillow() -> None:
        from pip import _internal

        _internal.main(["install", "pip", "setuptools", "wheel", "-U", "--user"])
        _internal.main(['install', 'Pillow', '--user'])
