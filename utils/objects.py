"""Object and mesh data utilities for Material Combiner.

This module provides functions for extracting and manipulating mesh data
like polygons and UV coordinates, which are essential for creating
properly mapped texture atlases.
"""

import math
from collections import defaultdict
from typing import Dict, List

import bpy
from mathutils import Vector


def get_polys(ob: bpy.types.Object) -> Dict[int, List[bpy.types.MeshPolygon]]:
    """Group polygons by material index.

    Args:
        ob: Mesh object to process.

    Returns:
        Dictionary mapping material indices to lists of polygons.
    """
    polys = defaultdict(list)
    for poly in ob.data.polygons:
        polys[poly.material_index].append(poly)
    return polys


def get_uv(ob: bpy.types.Object, poly: bpy.types.MeshPolygon) -> List[Vector]:
    """Get UV coordinates for a polygon.

    Extracts UV coordinates from the active UV layer for each loop in the polygon.

    Args:
        ob: Mesh object containing the polygon.
        poly: Polygon to extract UVs from.

    Returns:
        List of UV coordinate vectors for the polygon.
    """
    uv_data = ob.data.uv_layers.active.data
    return [
        uv_data[loop_idx].uv if loop_idx < len(uv_data) else Vector((0, 0, 0))
        for loop_idx in poly.loop_indices
    ]


def align_uv(face_uv: List[Vector]) -> List[Vector]:
    """Align UV coordinates to the positive quadrant.

    Shifts UV coordinates so they all start at the nearest integer
    grid point, preserving the relative positions.
    This handles UVs that extend beyond the 0-1 range.

    Args:
        face_uv: List of UV coordinate vectors to align.

    Returns:
        The modified UV coordinate list.
    """
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
