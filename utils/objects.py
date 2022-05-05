import math
from collections import defaultdict

from .. import globs


def get_obs(obs):
    return [ob for ob in obs if ob.type == 'MESH' and
            ob.data.uv_layers.active and not (ob.hide_get() if globs.version else ob.hide)]


# TODO: Optimise performance with numpy
def get_polys(ob):
    polys = defaultdict(list)
    for poly in ob.data.polygons:
        polys[poly.material_index].append(poly)
    return polys


# TODO: Optimise performance with numpy
def get_uv(ob, poly):
    return [ob.data.uv_layers.active.data[loop_idx].uv for loop_idx in poly.loop_indices if poly.loop_indices]


# TODO: Optimise performance with numpy
def align_uv(face_uv):
    min_x = min([math.floor(uv.x) if uv.x != 0.999 else 1 for uv in face_uv if not math.isnan(uv.x)], default=0)
    min_y = min([math.floor(uv.y) if uv.y != 0.999 else 1 for uv in face_uv if not math.isnan(uv.y)], default=0)
    for uv in face_uv:
        uv.x -= min_x
        uv.y -= min_y
    return face_uv
