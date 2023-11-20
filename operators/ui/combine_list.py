from collections import defaultdict
from typing import List
from typing import Set
from typing import cast

import bpy
from bpy.props import *

from ... import globs
from ...type_annotations import CombineListData
from ...type_annotations import Scene
from ...utils.materials import get_materials


class RefreshObData(bpy.types.Operator):
    bl_idname = 'smc.refresh_ob_data'
    bl_label = 'Combine List'
    bl_description = 'Updates the material list'

    @staticmethod
    def execute(self, context: bpy.types.Context) -> Set[str]:
        scn = context.scene
        ob_list = [ob for ob in context.visible_objects if
                   ob.type == 'MESH' and ob.data.uv_layers.active and ob.data.materials]
        combine_list_data = self._cache_previous_values(scn)
        self._rebuild_items_list(scn, ob_list, combine_list_data)
        return {'FINISHED'}

    @staticmethod
    def _cache_previous_values(scn: Scene) -> CombineListData:
        combine_list_data = cast(CombineListData, defaultdict(lambda: {
            'used': True,
            'mats': defaultdict(lambda: {
                'used': True,
                'layer': 1,
            }),
        }))

        for item in scn.smc_ob_data:
            if item.type == globs.CL_OBJECT:
                combine_list_data[item.ob]['used'] = item.used
            elif item.type == globs.CL_MATERIAL:
                mat_data = combine_list_data[item.ob]['mats'][item.mat]
                mat_data.update({'used': item.used, 'layer': item.layer})
        return combine_list_data

    def _rebuild_items_list(self, scn: Scene, ob_list: Set[bpy.types.Object],
                            combine_list_data: CombineListData) -> None:
        scn.smc_ob_data.clear()

        for ob_id, ob in enumerate(ob_list):
            ob_data = combine_list_data[ob]
            ob_used = ob_data['used']
            self._create_ob_item(scn, ob, ob_id, ob_used)

            for mat in get_materials(ob):
                if globs.is_blender_3_or_newer and not mat.preview:
                    mat.preview_ensure()

                mat_data = ob_data['mats'][mat]
                mat_used = ob_used and mat_data['used']
                mat_layer = mat_data['layer']
                self._create_mat_item(scn, ob, ob_id, mat, mat_used, mat_layer)
            self._create_separator_item(scn)

    @staticmethod
    def _create_ob_item(scn: Scene, ob: bpy.types.Object, ob_id: int, used: bool) -> None:
        item = scn.smc_ob_data.add()
        item.ob = ob
        item.ob_id = ob_id
        item.type = 0
        item.used = used

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
    def _switch_ob_state(data: List[bpy.types.PropertyGroup], item: bpy.types.PropertyGroup) -> None:
        mat_list = [mat for mat in data if mat.ob_id == item.ob_id and mat.type == globs.CL_MATERIAL]
        if not mat_list:
            return

        item.used = not item.used
        for mat in mat_list:
            mat.used = item.used

    @staticmethod
    def _switch_mat_state(data: List[bpy.types.PropertyGroup], item: bpy.types.PropertyGroup) -> None:
        ob = next((ob for ob in data if ob.ob_id == item.ob_id and ob.type == globs.CL_OBJECT), None)
        if not ob:
            return

        if not item.used:
            ob.used = True
        item.used = not item.used
