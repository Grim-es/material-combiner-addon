import bpy
from collections import defaultdict


def get_obs(obs):
    ob_list = []
    for ob in obs:
        if ob.type == 'MESH' and ob.data.uv_layers.active and not ob.hide:
            ob_list.append(ob)
    return ob_list


def get_polys(ob):
    polys = defaultdict(list)
    for poly in ob.data.polygons:
        polys[poly.material_index].append(poly)
    return polys


def get_uv(ob, poly):
    return [ob.data.uv_layers.active.data[loop_id].uv for loop_id in poly.loop_indices]


def get_loops(bm):
    loops = defaultdict(list) 
    for face in bm.faces:
        for loop in face.loops:
            loops[face].append(loop)
    return loops
