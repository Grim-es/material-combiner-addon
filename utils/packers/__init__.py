from typing import Dict

from .binary_tree_bin_packer import BinaryTreeBinPacker
from .max_rects_bin_packer import MaxRectsBinPacker
from .rectpack2D import RectPack2D


def pack(images: Dict, packer_type="MAX_RECTS"):
    packers = {
        "BINARY_TREE": BinaryTreeBinPacker,
        "RECT_PACK2D": RectPack2D,
        "MAX_RECTS": MaxRectsBinPacker,
    }

    packer = packers.get(packer_type, BinaryTreeBinPacker)()
    return packer.pack(images)
