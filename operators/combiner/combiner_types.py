from bpy.types import Material
from mathutils import Vector

from typing import Dict, List, Set, Tuple, Optional

from ...utils.type_hints import PixelSource, Size


# It would be nice to use a data class, but those don't exist in Blender 2.79's Python version and namedtuple can't be
# used as some attributes must be mutable.
# It would also be nice to use variable annotations, but those also don't exist in Blender 2.79's Python version


# __dict__ based baseclass
class _Base:
    def __repr__(self):
        items = ("{}={}".format(k, repr(v)) for k, v in self.__dict__.items())
        return "{}({})".format(type(self).__name__, ", ".join(items))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__


class Fit(_Base):
    def __init__(self, x=None, y=None):
        self.x = x
        self.y = y


class GFX(_Base):
    def __init__(self,
                 img: PixelSource = None,
                 size: Size = (),
                 uv_size: Tuple[float, float] = (),
                 fit: Optional[Fit] = None):
        self.pixel_source = img
        self.size = size
        self.uv_size = uv_size
        self.fit = fit


class RootMatData(_Base):
    def __init__(self,
                 gfx: GFX = None,
                 duplicate_materials: Set[str] = None,
                 objects_used_in: Set[str] = None,
                 uv_vectors: List[Vector] = None):
        self.gfx = GFX() if gfx is None else gfx
        self.duplicate_materials = set() if duplicate_materials is None else duplicate_materials
        self.objects_used_in = set() if objects_used_in is None else objects_used_in
        self.uv_vectors = [] if uv_vectors is None else uv_vectors

    def get_top_left_corner(self, scene):
        fit = self.gfx.fit
        if fit:
            x = fit.x + int(scene.smc_gaps / 2)
            y = fit.y + int(scene.smc_gaps / 2)
            return x, y
        else:
            return None


# Type hints
Data = Dict[str, Dict[Material, int]]
MatsUV = Dict[str, Dict[Material, List[Vector]]]
Structure = Dict[Material, RootMatData]
StructureItem = Tuple[Material, RootMatData]
