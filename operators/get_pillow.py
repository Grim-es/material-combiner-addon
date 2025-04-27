"""Pillow dependency installation for Material Combiner.

This module provides an operator to install the Pillow (PIL) library,
which is a required dependency for image processing in the Material Combiner.
It handles installation of pip if needed, and works across different Blender versions.
"""

import importlib.util
import os
import subprocess
import sys
from typing import Set

import bpy

from .. import globs


class InstallPIL(bpy.types.Operator):
    """Operator for installing the Pillow library.

    This operator checks if pip is available, installs it if needed,
    then installs the Pillow library for image processing.
    """

    bl_idname = "smc.get_pillow"
    bl_label = "Install PIL"
    bl_description = "Click to install Pillow. This could take a while and might require you to run Blender as Admin."

    def execute(self, context: bpy.types.Context) -> Set[str]:
        """Execute the Pillow installation process.

        Args:
            context: Current Blender context

        Returns:
            Status set indicating successful completion
        """
        pip_exists = importlib.util.find_spec("pip._internal") is not None
        pil_exists = all(
            importlib.util.find_spec(m) is not None
            for m in ("PIL", "PIL.Image", "PIL.ImageChops")
        )

        if not pip_exists:
            self._install_pip()
            self._install_pillow()
        elif not pil_exists:
            self._install_pillow()

        globs.pil_install_attempted = True

        self.report({"INFO"}, "Installation complete")
        return {"FINISHED"}

    def _install_pip(self) -> None:
        """Install pip using the appropriate method for the Blender version."""
        if globs.is_blender_modern:
            try:
                import ensurepip

                ensurepip.bootstrap()
            except ImportError:
                self._install_pip_clean()
        else:
            self._install_pip_clean()

    @staticmethod
    def _install_pip_clean() -> None:
        """Install pip manually using get-pip.py."""
        python_executable = (
            sys.executable
            if globs.is_blender_2_92_plus
            else bpy.app.binary_path_python
        )
        get_pip = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "get-pip.py"
        )
        subprocess.call(
            [python_executable, get_pip, "--user", "--force-reinstall"],
            shell=True,
        )

    @staticmethod
    def _install_pillow() -> None:
        """Install Pillow using pip."""
        from pip import _internal

        _internal.main(
            ["install", "pip", "setuptools", "wheel", "-U", "--user"]
        )
        _internal.main(['install', 'Pillow', '--user'])
