import math
from collections import defaultdict

from .. import globs


def get_obs(obs):
    return [ob for ob in obs if ob.type == 'MESH' and
            ob.data.uv_layers.active and not (ob.hide_get() if globs.is_blender_2_80_or_newer else ob.hide)]


# TODO: Optimise performance with numpy
def get_polys(ob):
    polys = defaultdict(list)
    for poly in ob.data.polygons:
        polys[poly.material_index].append(poly)
    return polys


# TODO: Optimise performance with numpy
def get_uv(ob, poly):
    """:return: all uvs in the object's active uv layer for the specified polygon"""
    if poly.loop_indices:
        return [ob.data.uv_layers.active.data[loop_idx].uv for loop_idx in poly.loop_indices]
    else:
        return []


# TODO: Optimise performance with numpy
def align_uv(face_uv):
    """Offsets face uvs so that their minimum x and y components lie within the standard (0,0) to (1,1) unit square.

    This is useful if all the uvs are 1 or a multiple of whole units offset from (0,0) to (1,1) and the material was
     reliant on the texture repeating when uvs fell outside the texture's bounds.

    For example, if all of your uv components were already in the bounds [0, n], where n > 0, and you were to move
     all the uvs by 1X and 2Y, the new bounds would be [0, n] + 1 = [1, n+1] for the x components
     and [0, n] + 2 = [2, n+2] for the y components. This function will find that the integer start of the X bound is 1
     and the integer start of the Y bound is 2 and subtract those amounts from the uvs so that the start bounds of both
     the X and Y components become 0.

    This won't be able to fix face uvs where the uvs cross over the boundary from one unit square to the next.
     For example, suppose the top left corner of a quad is at (0.9, 0.8) and the top right corner of a quad is at
     (1.1, 0.8), the minimum x component is already within the bounds [0,1] so no x offset will be done."""
    # Get all the x uvs and y uvs
    x_uvs = []
    y_uvs = []
    for uv in face_uv:
        if not math.isnan(uv.x):
            x_uvs.append(uv.x)
        if not math.isnan(uv.y):
            y_uvs.append(uv.y)
    # Find the minimum of both
    min_x = min(x_uvs, default=0)
    min_y = min(y_uvs, default=0)

    # Floor both minimums to get a whole number which is never more than the original
    min_x = math.floor(min_x)
    min_y = math.floor(min_y)

    # Offset all uvs by the floored minimum found
    # Usually this will do nothing as both will be 0
    # Note that this modifies the existing uvs
    if min_x != 0 or min_y != 0:
        for uv in face_uv:
            uv.x -= min_x
            uv.y -= min_y
