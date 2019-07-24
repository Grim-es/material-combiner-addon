import bpy
from bpy.props import *
from collections import defaultdict
from ... utils . objects import get_obs
from ... utils . materials import (
    get_materials,
    sort_materials
)


class RefreshObData(bpy.types.Operator):
    bl_idname = 'smc.refresh_ob_data'
    bl_label = 'Combine List'
    bl_description = 'Refresh Combine List'

    def execute(self, context):
        scn = context.scene
        ob_list = get_obs(scn.objects)
        combine_list = defaultdict(list)
        layers = defaultdict(dict)
        for i in scn.smc_ob_data:
            if i.type == 1:
                combine_list[i.ob].append(i.mat if i.used else [])
                layers[i.ob][i.mat] = i.layer
        scn.smc_ob_data.clear()
        for ob_id, ob in enumerate(ob_list):
            mat_dict = sort_materials(get_materials(ob))
            item = scn.smc_ob_data.add()
            item.ob = ob
            item.ob_id = ob_id
            item.type = 0
            for mats in mat_dict.values():
                for mat in mats:
                    item = scn.smc_ob_data.add()
                    if ob in combine_list.keys() and mat not in combine_list[ob]:
                        item.used = False
                    item.ob = ob
                    item.ob_id = ob_id
                    item.mat = mat
                    item.type = 1
                    if mat in layers[ob].keys():
                        item.layer = layers[ob][mat]
            item = scn.smc_ob_data.add()
            item.type = 2
        return {'FINISHED'}


class CombineSwitch(bpy.types.Operator):
    bl_idname = 'smc.combine_switch'
    bl_label = 'Add Item'
    bl_description = 'Select / Deselect'

    list_id = IntProperty(default=0)

    def execute(self, context):
        scn = context.scene
        items = scn.smc_ob_data
        item = items[self.list_id]
        if item.type:
            ob = next((ob for ob in items if (ob.ob_id == item.ob_id) and ob.type == 0), None)
            if ob:
                if item.used:
                    item.used = False
                else:
                    ob.used = True
                    item.used = True
        else:
            mat_list = [mat for mat in items if (mat.ob_id == item.ob_id) and mat.type != 0]
            if mat_list:
                if item.used:
                    for mat in mat_list:
                        mat.used = False
                    item.used = False
                else:
                    for mat in mat_list:
                        mat.used = True
                    item.used = True
        return {'FINISHED'}
