"""Pillow dependency installation for Material Combiner.

This module provides an operator to install the Pillow (PIL) library,
which is a required dependency for image processing in the Material Combiner.
It handles installation of pip if needed, and works across different Blender versions.

Usage example:
    bpy.ops.smc.get_pillow()
"""

import importlib.util
import os
import subprocess
import sys
from typing import Set

import bpy

from .. import globs


class InstallPIL(bpy.types.Operator):
    """Installs the Pillow library for image processing functionality.

    This operator first checks if pip is available in the current Blender
    installation, installs it if needed, then installs the Pillow library.
    May require administrative privileges depending on the system configuration.
    """

    bl_idname = "smc.get_pillow"
    bl_label = "Install PIL"
    bl_description = "Click to install Pillow. This could take a while and might require you to run Blender as Admin."

    def execute(self, context: bpy.types.Context) -> Set[str]:
        """Executes the Pillow installation process.

        Checks for pip and PIL dependencies, attempts to install them as needed,
        and reports success or failure to the user.

        Args:
            context: Current Blender context.

        Returns:
            Set containing "FINISHED" if the installation completes successfully,
            or "CANCELLED" if the installation fails.
        """
        has_pip = all(self._module_exists(m) for m in ("pip", "pip._internal"))
        has_pil = all(
            self._module_exists(m)
            for m in ("PIL", "PIL.Image", "PIL.ImageChops")
        )

        success = True
        if not has_pip:
            success = self._install_pip()
            if success:
                success = self._install_pillow()
        elif not has_pil:
            success = self._install_pillow()

        globs.pil_install_attempted = True

        self.report(
            {"INFO" if success else "ERROR"},
            "Installation complete" if success else "Installation failed",
        )
        return {"FINISHED"} if success else {"CANCELLED"}

    @staticmethod
    def _module_exists(module_name: str) -> bool:
        """Checks if a Python module exists in the current environment.

        Args:
            module_name: Name of the module to check for.

        Returns:
            True if the module exists, False otherwise.
        """
        return importlib.util.find_spec(module_name) is not None

    def _install_pip(self) -> bool:
        """Attempts to install pip using an appropriate method for the Blender version.

        For modern Blender versions, uses the built-in ensurepip module when available.
        Falls back to manual installation using get-pip.py for older versions.

        Returns:
            True if pip installation succeeds, False otherwise.
        """
        try:
            if globs.is_blender_modern:
                return self._try_install_pip_with_ensurepip()
            else:
                return self._install_pip_clean()
        except Exception as e:
            self.report({"ERROR"}, "Failed to install pip: {}".format(e))
            return False

    def _try_install_pip_with_ensurepip(self) -> bool:
        """Attempts to install pip using the ensurepip module.

        Uses Blender's built-in ensurepip module when available in modern versions.
        Falls back to manual installation if the module is not present or fails.

        Returns:
            True if pip installation succeeds, False otherwise.
        """
        try:
            import ensurepip

            ensurepip.bootstrap()
            return True
        except ImportError:
            return self._install_pip_clean()

    def _install_pip_clean(self) -> bool:
        """Installs pip manually using get-pip.py.

        Uses the embedded get-pip.py script to perform a clean installation
        of pip with user privileges. Captures and reports errors if they occur.

        Returns:
            True if pip installation succeeds, False otherwise.
        """
        try:
            python_executable = (
                sys.executable
                if globs.is_blender_2_92_plus
                else bpy.app.binary_path_python
            )
            get_pip = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "get-pip.py"
            )

            process = subprocess.run(
                [python_executable, get_pip, "--user", "--force-reinstall"],
                capture_output=True,
                text=True,
                shell=True,
                check=False,
            )

            if process.returncode != 0:
                self.report(
                    {"ERROR"}, "get-pip.py failed: {}".format(process.stderr)
                )
                return False

            return True
        except Exception as e:
            self.report({"ERROR"}, "Failed to run get-pip.py: {}".format(e))
            return False

    def _install_pillow(self) -> bool:
        """Installs Pillow using pip.

        First updates pip, setuptools, and wheel to ensure compatibility,
        then installs the Pillow package with user privileges. Captures
        and reports any errors encountered during the process.

        Returns:
            True if Pillow installation succeeds, False otherwise.
        """
        try:
            from pip import _internal

            deps_result = _internal.main(
                ["install", "pip", "setuptools", "wheel", "-U", "--user"]
            )
            if deps_result != 0:
                self.report({"ERROR"}, "Failed to update pip dependencies")
                return False

            pillow_result = _internal.main(["install", "Pillow", "--user"])
            if pillow_result != 0:
                self.report({"ERROR"}, "Failed to install Pillow")
                return False

            return True
        except ImportError:
            self.report({"ERROR"}, "Failed to import pip after installation")
            return False
        except Exception as e:
            self.report(
                {"ERROR"}, "Error during Pillow installation: {}".format(e)
            )
            return False
