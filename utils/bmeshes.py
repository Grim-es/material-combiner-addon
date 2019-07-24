import bpy
import bmesh
from collections import defaultdict


def get_loops(bm):
    loops = defaultdict(list)
    for face in bm.faces:
        for loop in face.loops:
            loops[face].append(loop)
    return loops
