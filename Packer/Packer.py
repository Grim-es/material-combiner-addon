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


class Packer(object):
    def __init__(self, images):
        self.root = {}
        self.images = images

    def fit(self):
        images = self.images
        img_len = len(self.images)
        w = 0
        h = 0
        if img_len > 0:
            w = images[0]['w']
            h = images[0]['h']
        self.root = {'x': 0, 'y': 0, 'w': w, 'h': h}
        for img in images:
            if self.findNode(self.root, img['w'], img['h']) is not None:
                node = self.findNode(self.root, img['w'], img['h'])
                img['fit'] = self.splitNode(node, img['w'], img['h'])
            else:
                img['fit'] = self.growNode(img['w'], img['h'])
        return images

    def findNode(self, root, w, h):
        if 'used' in root and root['used']:
                return self.findNode(root['right'], w, h) or self.findNode(root['down'], w, h)
        elif (w <= root['w']) and (h <= root['h']):
            return root
        else:
            return None

    def splitNode(self, node, w, h):
        node['used'] = True
        node['down'] = {'x': node['x'], 'y': node['y'] + h, 'w': node['w'], 'h': node['h'] - h}
        node['right'] = {'x': node['x'] + w, 'y': node['y'], 'w': node['w'] - w, 'h': h}
        return node

    def growNode(self, w, h):
        canGrowDown = (w <= self.root['w'])
        canGrowRight = (h <= self.root['h'])

        shouldGrowRight = canGrowRight and (self.root['h'] >= (self.root['w'] + w))
        shouldGrowDown = canGrowDown and (self.root['w'] >= (self.root['h'] + h))

        if shouldGrowRight:
            return self.growRight(w, h)
        elif shouldGrowDown:
            return self.growDown(w, h)
        elif canGrowRight:
            return self.growRight(w, h)
        elif canGrowDown:
            return self.growDown(w, h)
        else:
            return None

    def growRight(self, w, h):
        self.root = {
            'used': True,
            'x': 0,
            'y': 0,
            'w': self.root['w'] + w,
            'h': self.root['h'],
            'down': self.root,
            'right': {'x': self.root['w'], 'y': 0, 'w': w, 'h': self.root['h']}}
        if self.findNode(self.root, w, h) is not None:
            node = self.findNode(self.root, w, h)
            return self.splitNode(node, w, h)
        else:
            return None

    def growDown(self, w, h):
        self.root = {
            'used': True,
            'x': 0,
            'y': 0,
            'w': self.root['w'],
            'h': self.root['h'] + h,
            'down': {'x': 0, 'y': self.root['h'], 'w': self.root['w'], 'h': h},
            'right': self.root
        }
        if self.findNode(self.root, w, h) is not None:
            node = self.findNode(self.root, w, h)
            return self.splitNode(node, w, h)
        else:
            return None
