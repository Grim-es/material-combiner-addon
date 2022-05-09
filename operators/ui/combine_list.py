from collections import defaultdict

import bpy
from bpy.props import *
from ...utils.materials import get_materials
from ...utils.materials import sort_materials
from ...utils.objects import get_obs
from ... import globs

class RefreshObData(bpy.types.Operator):
    bl_idname = 'smc.refresh_ob_data'
    bl_label = 'Combine List'
    bl_description = 'Updates the material list'

    def execute(self, context):
        scn = context.scene
        # We don't want users to lose all the settings of their current material list when updating it, so get
        # The used materials for each old object
        old_obs_to_used_materials = defaultdict(set)
        # The layer for each material for each old object
        old_layers = defaultdict(dict)
        for old_combine_item in scn.smc_ob_data:
            if old_combine_item.type == globs.C_L_MATERIAL:
                # It's important that we always get the used materials list so that even if an object had no used
                # materials, it still gets added to the dictionary
                used_materials = old_obs_to_used_materials[old_combine_item.ob]
                if old_combine_item.used:
                    used_materials.add(old_combine_item.mat)
                old_layers[old_combine_item.ob][old_combine_item.mat] = old_combine_item.layer
        # Clear the old data from the scene
        scn.smc_ob_data.clear()
        # Iterate through all the non-hidden mesh objects in the scene
        for idx, ob in enumerate(get_obs(scn.objects)):
            mat_dict = sort_materials(get_materials(ob))
            item = scn.smc_ob_data.add()
            item.type = globs.C_L_OBJECT
            item.ob = ob
            item.ob_id = idx
            old_mats_layers = old_layers[ob]
            for mats in mat_dict.values():
                for mat in mats:
                    if mat:
                        item = scn.smc_ob_data.add()
                        item.type = globs.C_L_MATERIAL
                        # If the current object was in the old combine list, but either the material didn't exist or was
                        # set to not be used, set it to not be used in the new combine list
                        if ob in old_obs_to_used_materials and mat not in old_obs_to_used_materials[ob]:
                            item.used = False
                        item.ob = ob
                        item.ob_id = idx
                        item.mat = mat
                        if mat in old_mats_layers:
                            item.layer = old_mats_layers[mat]
            # TODO: Does this need to exist?
            item = scn.smc_ob_data.add()
            item.type = globs.C_L_END
        return {'FINISHED'}


class CombineSwitch(bpy.types.Operator):
    bl_idname = 'smc.combine_switch'
    bl_label = 'Add Item'
    bl_description = 'Selected materials will be combined into one texture atlas'

    list_id = IntProperty(default=0)

    def execute(self, context):
        scn = context.scene
        items = scn.smc_ob_data
        item = items[self.list_id]
        # TODO: Probably can ignore C_L_END types?
        if item.type == globs.C_L_MATERIAL or item.type == globs.C_L_END:
            # Get the OBJECT type item with the same ob_id as this item
            ob_item = next((ob for ob in items if (ob.ob_id == item.ob_id) and ob.type == globs.C_L_OBJECT), None)
            if ob_item:
                if item.used:
                    item.used = False
                else:
                    ob_item.used = True
                    item.used = True
        else:
            mat_item_list = [mat for mat in items if (mat.ob_id == item.ob_id) and mat.type != globs.C_L_OBJECT]
            if mat_item_list:
                if item.used:
                    for mat in mat_item_list:
                        mat.used = False
                    item.used = False
                else:
                    for mat in mat_item_list:
                        mat.used = True
                    item.used = True
        return {'FINISHED'}
