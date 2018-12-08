# MIT License

# Copyright (c) 2018 shotariya

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


bl_info = {
    'name': "Shotariya's Material Combiner",
    'description': 'Public Release Material Combiner 2',
    'author': 'shotariya',
    'version': (2, 0, 3, 1),
    'blender': (2, 79, 0),
    'location': 'View3D',
    # 'warning': '',
    'wiki_url': 'https://vrcat.club/threads/material-combiner-blender-addon.2255/',
    'category': 'Object'}

iamready = True

import bpy
import os
from subprocess import call
try:
    import pip
    try:
        from PIL import Image, ImageChops
    except ImportError:
        call([bpy.app.binary_path_python, '-m', 'pip', 'install', 'Pillow', '--user', '--upgrade'], shell=True)
        iamready = False
except ImportError:
    call([bpy.app.binary_path_python,
          os.path.join(os.path.dirname(os.path.abspath(__file__)), 'get-pip.py'), '--user'], shell=True)
    call([bpy.app.binary_path_python, '-m', 'pip', 'install', 'Pillow', '--user', '--upgrade'], shell=True)
    iamready = False


from . import developer_utils
modules = developer_utils.setup_addon_modules(__path__, __name__, 'bpy' in locals())

import bpy.utils.previews
from . registration import register_all, unregister_all


def register():
    bpy.utils.register_module(__name__)
    register_all()
    print('Registered {} with {} modules'.format(bl_info['name'], len(modules)))


def unregister():
    bpy.utils.unregister_module(__name__)
    unregister_all()
    print('Unregistered {}'.format(bl_info['name']))
