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
    'version': (2, 1, 1, 2),
    'blender': (2, 80, 0),
    'location': 'View3D',
    # 'warning': '',
    'wiki_url': 'https://vrcat.club/threads/material-combiner-blender-addon.2255/',
    'category': 'Object'}

from .registration import register_all
from .registration import unregister_all


def register():
    print('Loading Material Combiner..')
    register_all(bl_info)


def unregister():
    unregister_all()
