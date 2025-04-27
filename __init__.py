"""Material Combiner Addon for Blender.

This addon reduces draw calls in game engines by combining multiple material textures
into a single atlas while preserving quality and handling UV coordinates properly.
It supports material blending, texture optimization, and provides a user-friendly interface.

MIT License

Copyright (c) 2018 shotariya

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

bl_info = {
    "name": "Shotariya's Material Combiner",
    "description": "Advanced Texture Atlas Generation System",
    "author": "shotariya",
    "version": (2, 1, 3, 0),
    "blender": (2, 80, 0),
    "location": "View3D",
    "wiki_url": "https://github.com/Grim-es/material-combiner-addon",
    "tracker_url": "https://github.com/Grim-es/material-combiner-addon/issues",
    "category": "Object",
}

from .registration import register_all, unregister_all  # noqa: E402


def register() -> None:
    """Register the addon with Blender.

    Blender calls this function when enabling the addon.
    It delegates to the registration module to initialize all components.
    """
    print("Loading Material Combiner..")
    register_all(bl_info)


def unregister() -> None:
    """Unregister the addon from Blender.

    Blender calls this function when disabling the addon.
    It delegates to the registration module to clean up all components.
    """
    unregister_all()
