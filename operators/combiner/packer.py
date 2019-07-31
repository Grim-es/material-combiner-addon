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


class BinPacker(object):
    def __init__(self, images):
        self.root = {}
        self.bin = images

    def fit(self):
        images = self.bin
        img_len = len(self.bin)
        w = 0
        h = 0
        if img_len > 0:
            w, h = images[next(iter(images))]['gfx']['size'] if \
                images[next(iter(images))]['gfx']['crop']['size'] is None else \
                images[next(iter(images))]['gfx']['crop']['size']
        self.root = {'x': 0, 'y': 0, 'w': w, 'h': h}
        for img in images.values():
            w, h = img['gfx']['size'] if img['gfx']['crop']['size'] is None else img['gfx']['crop']['size']
            if self.find_node(self.root, w, h):
                node = self.find_node(self.root, w, h)
                img['gfx']['fit'] = self.split_node(node, w, h)
            else:
                img['gfx']['fit'] = self.grow_node(w, h)
        return images

    def find_node(self, root, w, h):
        if 'used' in root and root['used']:
            return self.find_node(root['right'], w, h) or self.find_node(root['down'], w, h)
        elif (w <= root['w']) and (h <= root['h']):
            return root
        return None

    def split_node(self, node, w, h):
        node['used'] = True
        node['down'] = {'x': node['x'], 'y': node['y'] + h, 'w': node['w'], 'h': node['h'] - h}
        node['right'] = {'x': node['x'] + w, 'y': node['y'], 'w': node['w'] - w, 'h': h}
        return node

    def grow_node(self, w, h):
        can_grow_right = (h <= self.root['h'])
        can_grow_down = (w <= self.root['w'])

        should_grow_right = can_grow_right and (self.root['h'] >= (self.root['w'] + w))
        should_grow_down = can_grow_down and (self.root['w'] >= (self.root['h'] + h))

        if should_grow_right:
            return self.grow_right(w, h)
        elif should_grow_down:
            return self.grow_down(w, h)
        elif can_grow_right:
            return self.grow_right(w, h)
        elif can_grow_down:
            return self.grow_down(w, h)
        return None

    def grow_right(self, w, h):
        self.root = {
            'used': True,
            'x': 0,
            'y': 0,
            'w': self.root['w'] + w,
            'h': self.root['h'],
            'down': self.root,
            'right': {'x': self.root['w'], 'y': 0, 'w': w, 'h': self.root['h']}}
        if self.find_node(self.root, w, h):
            node = self.find_node(self.root, w, h)
            return self.split_node(node, w, h)
        return None

    def grow_down(self, w, h):
        self.root = {
            'used': True,
            'x': 0,
            'y': 0,
            'w': self.root['w'],
            'h': self.root['h'] + h,
            'down': {'x': 0, 'y': self.root['h'], 'w': self.root['w'], 'h': h},
            'right': self.root
        }
        if self.find_node(self.root, w, h):
            node = self.find_node(self.root, w, h)
            return self.split_node(node, w, h)
        return None
