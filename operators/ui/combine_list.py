from collections import defaultdict
from typing import DefaultDict
from typing import Dict
from typing import List
from typing import Set
from typing import Tuple

import bpy
from bpy.props import *

from ... import globs
from ...type_annotations import ObMats
from ...type_annotations import SMCObData
from ...type_annotations import SMCObDataItem
from ...type_annotations import Scene
from ...utils.materials import get_materials
from ...utils.materials import sort_materials


class RefreshObData(bpy.types.Operator):
    bl_idname = 'smc.refresh_ob_data'
    bl_label = 'Combine List'
    bl_description = 'Updates the material list'

    @staticmethod
    def execute(self, context: bpy.types.Context) -> Set[str]:
        scn = context.scene
        ob_list = [ob for ob in context.visible_objects if
                   ob.type == 'MESH' and ob.data.uv_layers.active and ob.data.materials]
        combine_list, layers = self._cache_previous_values(scn)
        self._rebuild_items_list(scn, ob_list, combine_list, layers)
        return {'FINISHED'}

    @staticmethod
    def _cache_previous_values(scn: Scene) -> Tuple[
        DefaultDict[bpy.types.Object, ObMats],
        DefaultDict[bpy.types.Object, Dict[ObMats, int]]
    ]:

        combine_list = defaultdict(list)
        layers = defaultdict(dict)
        for item in scn.smc_ob_data:
            if item.type == globs.CL_MATERIAL:
                if item.used:
                    combine_list[item.ob].append(item.mat)
                layers[item.ob][item.mat] = item.layer
        return combine_list, layers

    def _rebuild_items_list(self, scn: Scene, ob_list: List[bpy.types.Object],
                            combine_list: DefaultDict[bpy.types.Object, ObMats],
                            layers: DefaultDict[bpy.types.Object, Dict[ObMats, int]]) -> None:
        scn.smc_ob_data.clear()

        for ob_id, ob in enumerate(ob_list):
            mat_dict = sort_materials(get_materials(ob))
            self._create_ob_item(scn, ob, ob_id)
            for mats in mat_dict:
                for mat in mats:
                    if mat:
                        if globs.is_blender_3_or_newer and not mat.preview:
                            mat.preview_ensure()
                        used = ob not in combine_list or mat in combine_list[ob]
                        layer = layers[ob][mat] if mat in layers[ob] else 1
                        self._create_mat_item(scn, ob, ob_id, mat, used, layer)
            self._create_separator_item(scn)

    @staticmethod
    def _create_ob_item(scn: Scene, ob: bpy.types.Object, ob_id: int) -> None:
        item = scn.smc_ob_data.add()
        item.ob = ob
        item.ob_id = ob_id
        item.type = 0

    @staticmethod
    def _create_mat_item(scn: Scene, ob: bpy.types.Object, ob_id: int, mat: bpy.types.Material, used: bool,
                         layer: int) -> None:
        item = scn.smc_ob_data.add()
        item.ob = ob
        item.ob_id = ob_id
        item.mat = mat
        item.type = 1
        item.used = used
        item.layer = layer

    @staticmethod
    def _create_separator_item(scn: Scene) -> None:
        item = scn.smc_ob_data.add()
        item.type = 2


class CombineSwitch(bpy.types.Operator):
    bl_idname = 'smc.combine_switch'
    bl_label = 'Add Item'
    bl_description = 'Selected materials will be combined into one texture atlas'

    list_id = IntProperty(default=0)

    def execute(self, context: bpy.types.Context) -> Set[str]:
        scn = context.scene
        data = scn.smc_ob_data
        item = data[self.list_id]
        if item.type == globs.CL_OBJECT:
            self._switch_ob_state(data, item)
        elif item.type == globs.CL_MATERIAL:
            self._switch_mat_state(data, item)
        return {'FINISHED'}

    @staticmethod
    def _switch_ob_state(data: SMCObData, item: SMCObDataItem) -> None:
        mat_list = [mat for mat in data if mat.ob_id == item.ob_id and mat.type == globs.CL_MATERIAL]
        if mat_list:
            item.used = not item.used
            for mat in mat_list:
                mat.used = item.used

    @staticmethod
    def _switch_mat_state(data: SMCObData, item: SMCObDataItem) -> None:
        ob = next((ob for ob in data if ob.ob_id == item.ob_id and ob.type == globs.CL_OBJECT), None)
        if ob:
            if not item.used:
                ob.used = True
            item.used = not item.used
