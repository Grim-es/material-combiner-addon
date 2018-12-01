import bpy


class MatTexItemAdd(bpy.types.Operator):
    bl_idname = 'smc.layer_add'
    bl_label = 'Add Item'

    def execute(self, context):
        scn = context.scene
        item = scn.smc_layers.add()
        num = len(scn.smc_layers) - 1
        item.layer = 'Layer {}'.format(scn.smc_layers_name_id)
        scn.smc_layers_id = num
        scn.smc_layers_name_id += 1
        return {'FINISHED'}


class MatTexItemRemove(bpy.types.Operator):
    bl_idname = 'smc.layer_remove'
    bl_label = 'Remove Item'

    def execute(self, context):
        scn = context.scene
        if len(scn.smc_layers) > 1:
            scn.smc_layers.remove(scn.smc_layers_id)
        else:
            scn.smc_layers[scn.smc_layers_id].layer = 'Layer 1'
        if scn.smc_layers_id > (len(scn.smc_layers) - 1):
            scn.smc_layers_id = scn.smc_layers_id - 1
        return {'FINISHED'}
