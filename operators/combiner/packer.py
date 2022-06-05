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
from .combiner_types import Structure, Fit


class Node(Fit):
    def __init__(self, x, y, w, h, used=False, down=None, right=None):
        super().__init__(x, y)
        self.w = w
        self.h = h
        self.used = used
        self.down = down
        self.right = right

    def split(self, w, h):
        self.used = True
        self.down = Node(x=self.x, y=self.y + h, w=self.w, h=self.h - h)
        self.right = Node(x=self.x + w, y=self.y, w=self.w - w, h=h)
        return self

    def find(self, w, h):
        if self.used:
            return self.right.find(w, h) or self.down.find(w, h)
        elif (w <= self.w) and (h <= self.h):
            return self
        return None


class BinPacker(object):
    def __init__(self, structure: Structure):
        self.root = None
        self.bin = structure

    def fit(self):
        structure = self.bin
        structure_len = len(self.bin)
        w = 0
        h = 0
        if structure_len > 0:
            w, h = structure[next(iter(structure))].gfx.size
        self.root = Node(x=0, y=0, w=w, h=h)
        for img in structure.values():
            w, h = img.gfx.size
            node = self.root.find(w, h)
            if node:
                img.gfx.fit = node.split(w, h)
            else:
                img.gfx.fit = self.grow_node(w, h)
        return structure

    def grow_node(self, w, h):
        can_grow_right = (h <= self.root.h)
        can_grow_down = (w <= self.root.w)

        should_grow_right = can_grow_right and (self.root.h >= (self.root.w + w))
        should_grow_down = can_grow_down and (self.root.w >= (self.root.h + h))

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
        self.root = Node(
            used=True,
            x=0,
            y=0,
            w=self.root.w + w,
            h=self.root.h,
            down=self.root,
            right=Node(x=self.root.w, y=0, w=w, h=self.root.h))
        node = self.root.find(w, h)
        if node:
            return node.split(w, h)
        return None

    def grow_down(self, w, h):
        self.root = Node(
            used=True,
            x=0,
            y=0,
            w=self.root.w,
            h=self.root.h + h,
            down=Node(x=0, y=self.root.h, w=self.root.w, h=h),
            right=self.root
        )
        node = self.root.find(w, h)
        if node:
            return node.split(w, h)
        return None
