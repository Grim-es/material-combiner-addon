from collections import defaultdict

import bpy

from .material_source import MaterialSource
from ..globs import debug_print


def get_materials(ob):
    return [mat_slot.material for mat_slot in ob.material_slots]


def sort_materials(mat_list):
    for mat in bpy.data.materials:
        mat.root_mat = None
    mat_dict = defaultdict(list)
    for mat in mat_list:
        material_source = MaterialSource.from_material(mat)
        multiply_by_diffuse = mat.smc_diffuse if mat else False
        sort_key = material_source.to_sort_key(multiply_by_diffuse)
        debug_print("DEBUG: Sort key for {} is {}".format(mat, sort_key))
        mat_dict[sort_key].append(mat)
    return mat_dict
