import math
from collections import defaultdict
from typing import List, Dict

import bpy
from mathutils import Vector


def get_polys(ob: bpy.types.Object) -> Dict[int, bpy.types.MeshPolygon]:
    polys = defaultdict(list)
    for poly in ob.data.polygons:
        polys[poly.material_index].append(poly)
    return polys


def get_uv(ob: bpy.types.Object, poly: bpy.types.MeshPolygon) -> List[Vector]:
    data = ob.data.uv_layers.active.data
    return [data[loop_idx].uv if loop_idx < len(data) else Vector((0, 0, 0)) for loop_idx in poly.loop_indices]


def align_uv(face_uv: List[Vector]) -> List[Vector]:
    min_x = float('inf')
    min_y = float('inf')

    for uv in face_uv:
        if not math.isnan(uv.x):
            min_x = min(min_x, uv.x)
        if not math.isnan(uv.y):
            min_y = min(min_y, uv.y)

    min_x = math.floor(min_x)
    min_y = math.floor(min_y)

    if min_x != 0 or min_y != 0:
        for uv in face_uv:
            uv.x -= min_x
            uv.y -= min_y
    return face_uv
