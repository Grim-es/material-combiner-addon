# Copyright (c) 2011, 2012, 2013, 2014, 2015, 2016 Jake Gordon and contributors
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from typing import Union
from typing import Dict


class BinPacker(object):
    def __init__(self, images: Dict) -> None:
        self.root = {}
        self.bin = images

    def fit(self) -> Dict:
        self.root = {'x': 0, 'y': 0, 'w': 0, 'h': 0}

        if not self.bin:
            return self.bin

        self.root['w'], self.root['h'] = next(iter(self.bin.values()))['gfx']['size']

        for img in self.bin.values():
            w, h = img['gfx']['size']
            node = self.find_node(self.root, w, h)
            img['gfx']['fit'] = self.split_node(node, w, h) if node else self.grow_node(w, h)

        return self.bin

    def find_node(self, root: Dict, w: int, h: int) -> Union[Dict, None]:
        if 'used' in root and root['used']:
            return self.find_node(root['right'], w, h) or self.find_node(root['down'], w, h)
        elif w <= root['w'] and h <= root['h']:
            return root
        return None

    @staticmethod
    def split_node(node: Dict, w: int, h: int) -> Dict:
        node['used'] = True
        node['down'] = {'x': node['x'], 'y': node['y'] + h, 'w': node['w'], 'h': node['h'] - h}
        node['right'] = {'x': node['x'] + w, 'y': node['y'], 'w': node['w'] - w, 'h': h}
        return node

    def grow_node(self, w: int, h: int) -> Union[Dict, None]:
        can_grow_right = h <= self.root['h']
        can_grow_down = w <= self.root['w']

        should_grow_right = can_grow_right and self.root['h'] >= self.root['w'] + w
        should_grow_down = can_grow_down and self.root['w'] >= self.root['h'] + h

        if should_grow_right or not should_grow_down and can_grow_right:
            return self.grow_right(w, h)
        elif should_grow_down or can_grow_down:
            return self.grow_down(w, h)
        return None

    def grow_right(self, w: int, h: int) -> Union[Dict, None]:
        self.root = {
            'used': True,
            'x': 0,
            'y': 0,
            'w': self.root['w'] + w,
            'h': self.root['h'],
            'down': self.root,
            'right': {'x': self.root['w'], 'y': 0, 'w': w, 'h': self.root['h']}
        }
        node = self.find_node(self.root, w, h)
        return self.split_node(node, w, h) if node else None

    def grow_down(self, w: int, h: int) -> Union[Dict, None]:
        self.root = {
            'used': True,
            'x': 0,
            'y': 0,
            'w': self.root['w'],
            'h': self.root['h'] + h,
            'down': {'x': 0, 'y': self.root['h'], 'w': self.root['w'], 'h': h},
            'right': self.root
        }
        node = self.find_node(self.root, w, h)
        return self.split_node(node, w, h) if node else None
