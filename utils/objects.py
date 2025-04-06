import math
from collections import defaultdict
from typing import Dict, List

import bpy
from mathutils import Vector


def get_polys(ob: bpy.types.Object) -> Dict[int, bpy.types.MeshPolygon]:
    polys = defaultdict(list)
    for poly in ob.data.polygons:
        polys[poly.material_index].append(poly)
    return polys


def get_uv(ob: bpy.types.Object, poly: bpy.types.MeshPolygon) -> List[Vector]:
    uv_data = ob.data.uv_layers.active.data
    return [
        uv_data[loop_idx].uv if loop_idx < len(uv_data) else Vector((0, 0, 0))
        for loop_idx in poly.loop_indices
    ]


def align_uv(face_uv: List[Vector]) -> List[Vector]:
    min_x = min((uv.x for uv in face_uv if not math.isnan(uv.x)), default=0.0)
    min_y = min((uv.y for uv in face_uv if not math.isnan(uv.y)), default=0.0)

    # Floor values for alignment
    min_x, min_y = math.floor(min_x), math.floor(min_y)

    # Shift UVs to align to (0,0)
    if min_x != 0 or min_y != 0:
        for uv in face_uv:
            uv.x -= min_x
            uv.y -= min_y

    return face_uv
