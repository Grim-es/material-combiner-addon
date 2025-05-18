"""Bin packing algorithm for optimally arranging textures in atlases.

This module provides a binary tree based bin packing algorithm for
efficiently packing multiple textures into a single atlas. The algorithm
grows the atlas as needed to fit all textures while trying to minimize wasted space.

Original algorithm by Jake Gordon
https://github.com/jakesgordon/bin-packing

Copyright (c) 2011, 2012, 2013, 2014, 2015, 2016 Jake Gordon and contributors

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

Typical usage example:
    images = {
        'mat1': {'gfx': {'size': (100, 200)}},
        'mat2': {'gfx': {'size': (150, 100)}}
    }
    packer = BinaryTreeBinPacker()
    packed_result = packer.pack(images)
"""

from typing import Dict, Optional


class BinaryTreeBinPacker:
    """Binary tree-based bin packing algorithm.

    This packing algorithm attempts to efficiently arrange rectangular textures
    in a minimal container size. It works by:
    1. Starting with an empty bin.
    2. Finding a node where a texture can fit.
    3. Splitting that node to leave the remaining space available.
    4. Growing the bin if needed when items don't fit.

    Attributes:
        root: The root node of the packing tree.
        bin: Dictionary of images to be packed with their data.
    """

    def __init__(self) -> None:
        """Initialize the bin packer with a set of images.

        Args:
            images: Dictionary of materials and their image/size data.
        """
        self.root = {}

    def pack(self, images: Dict) -> Dict:
        """Pack all textures into the bin.

        This method places all textures in optimal positions within the atlas.
        It updates each texture's entry with position data in the 'fit' field.

        Args:
            images: Dictionary of materials and their image/size data.
                    Each item should have the format:
                    {material_id: {'gfx': {'size': (width, height)}}}

        Returns:
            The updated bin dictionary with position information in each item's
            'gfx.fit' field, containing x, y coordinates, width and height.
        """
        self.bin = images
        self.root = {"x": 0, "y": 0, "w": 0, "h": 0}

        if not self.bin:
            return self.bin

        self.root["w"], self.root["h"] = next(iter(self.bin.values()))["gfx"][
            "size"
        ]

        for img in self.bin.values():
            w, h = img["gfx"]["size"]
            node = self.find_node(self.root, w, h)
            img["gfx"]["fit"] = (
                self.split_node(node, w, h) if node else self.grow_node(w, h)
            )

        return self.bin

    def find_node(self, root: Dict, w: int, h: int) -> Optional[Dict]:
        """Find a node in the tree that can accommodate the specified dimensions.

        Args:
            root: Current node to check.
            w: Width required.
            h: Height required.

        Returns:
            Suitable node or None if none is found.
        """
        if root.get("used"):
            return self.find_node(root["right"], w, h) or self.find_node(
                root["down"], w, h
            )
        elif w <= root["w"] and h <= root["h"]:
            return root
        return None

    @staticmethod
    def split_node(node: Dict, w: int, h: int) -> Dict:
        """Split a node to fit the specified dimensions.

        Creates 'down' and 'right' child nodes with the remaining space.

        Args:
            node: Node to split.
            w: Width required.
            h: Height required.

        Returns:
            The original node, now marked as used.
        """
        node["used"] = True
        node["down"] = {
            "x": node["x"],
            "y": node["y"] + h,
            "w": node["w"],
            "h": node["h"] - h,
        }
        node["right"] = {
            "x": node["x"] + w,
            "y": node["y"],
            "w": node["w"] - w,
            "h": h,
        }
        return node

    def grow_node(self, w: int, h: int) -> Optional[Dict]:
        """Grow the root node to accommodate a texture that doesn't fit.

        Decides whether to grow right or down based on which produces
        the more optimal overall shape.

        Args:
            w: Width required.
            h: Height required.

        Returns:
            A suitable node or None if growing isn't possible.
        """
        can_grow_right = h <= self.root["h"]
        can_grow_down = w <= self.root["w"]

        should_grow_right = (
            can_grow_right and self.root["h"] >= self.root["w"] + w
        )
        should_grow_down = (
            can_grow_down and self.root["w"] >= self.root["h"] + h
        )

        if should_grow_right or (not should_grow_down and can_grow_right):
            return self.grow_right(w, h)
        elif should_grow_down or can_grow_down:
            return self.grow_down(w, h)
        return None

    def grow_right(self, w: int, h: int) -> Optional[Dict]:
        """Grow the bin to the right.

        Args:
            w: Width to grow by.
            h: Height required.

        Returns:
            A suitable node or None if finding one fails.
        """
        self.root = {
            "used": True,
            "x": 0,
            "y": 0,
            "w": self.root["w"] + w,
            "h": self.root["h"],
            "down": self.root,
            "right": {"x": self.root["w"], "y": 0, "w": w, "h": self.root["h"]},
        }
        node = self.find_node(self.root, w, h)
        return self.split_node(node, w, h) if node else None

    def grow_down(self, w: int, h: int) -> Optional[Dict]:
        """Grow the bin downward.

        Args:
            w: Width required.
            h: Height to grow by.

        Returns:
            A suitable node or None if finding one fails.
        """
        self.root = {
            "used": True,
            "x": 0,
            "y": 0,
            "w": self.root["w"],
            "h": self.root["h"] + h,
            "down": {"x": 0, "y": self.root["h"], "w": self.root["w"], "h": h},
            "right": self.root,
        }
        node = self.find_node(self.root, w, h)
        return self.split_node(node, w, h) if node else None
