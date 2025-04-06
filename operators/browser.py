import re
import webbrowser
from typing import Set, Tuple

import bpy
from bpy.props import StringProperty

URL_PATTERN = r"^https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+"


class OpenBrowser(bpy.types.Operator):
    """
    Opens a web browser with the specified URL.

    This operator validates the URL for correct formatting and
    security concerns before attempting to open it in the user's
    default web browser.
    """

    bl_idname = "smc.browser"
    bl_label = "Open Web Browser"
    bl_description = "Open the specified URL in your default web browser"

    link = StringProperty(name="URL", description="Web address to open", default="")

    def execute(self, context: bpy.types.Context) -> Set[str]:
        valid, message = self._validate_url()
        if not valid:
            self.report({"ERROR"}, message)
            return {"CANCELLED"}

        try:
            webbrowser.open(self.link, new=2, autoraise=True)
            return {"FINISHED"}
        except Exception as e:
            self.report({"ERROR"}, "Failed to open browser: {0}".format(str(e)))
            return {"CANCELLED"}

    def _validate_url(self) -> Tuple[bool, str]:
        """
        Validate the URL for correctness and security.

        Returns:
            Tuple containing (is_valid, error_message)
        """
        if not self.link:
            return False, "URL cannot be empty"

        if not re.match(URL_PATTERN, self.link):
            return False, "Invalid URL format. Must begin with http:// or https://"

        if self.link.startswith("http://"):
            self.report({"WARNING"}, "Consider using HTTPS for better security")

        return True, ""
