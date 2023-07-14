from typing import Any
from typing import List
from typing import Optional
from typing import Tuple

import bpy

from . import globs
from .type_annotations import SMCObData


class SMC_UL_Combine_List(bpy.types.UIList):
    def draw_item(self, context: bpy.types.Context, layout: bpy.types.UILayout, data: Any, item: Any, icon: int,
                  active_data: Any,
                  active_propname: str, index: Optional[int]) -> None:
        row = layout.row(align=True)
        if item.type == globs.CL_OBJECT:
            self._draw_object(row, item, index)
        elif item.type == globs.CL_MATERIAL:
            self._draw_mat(row, item, index)

    @staticmethod
    def _draw_object(row: bpy.types.UILayout, item: Any, index: int) -> None:
        row.prop(item.ob, 'name', text='', icon='META_CUBE' if globs.is_blender_2_80_or_newer else 'VIEW3D', emboss=False)
        row = row.row()
        row.alignment = 'RIGHT'
        row.operator('smc.combine_switch',
                     text='Deselect All' if item.used else 'Select All',
                     emboss=False).list_id = index

    @staticmethod
    def _draw_mat(row: bpy.types.UILayout, item: Any, index: int) -> None:
        row.separator()
        row.label(text='', icon_value=item.mat.preview.icon_id if item.mat.preview else 'QUESTION')
        row.prop(item.mat, 'name', text='')
        col = row.column(align=True)
        col.alignment = 'RIGHT'
        col.scale_x = 0.6
        col.prop(item, 'layer', text='')
        if item.used:
            icon = 'CHECKBOX_HLT' if globs.is_blender_2_80_or_newer else 'FILE_TICK'
        else:
            icon = 'CHECKBOX_DEHLT' if globs.is_blender_2_80_or_newer else 'LAYER_USED'
        row.operator('smc.combine_switch', text='', icon=icon).list_id = index
        row.operator('smc.property_menu', text='',
                     icon='PREFERENCES' if globs.is_blender_2_80_or_newer else 'SCRIPT').list_id = index

    def filter_items(self, context: bpy.types.Context, data: Any, propname: str) -> Tuple[List[int], List[int]]:
        data = getattr(data, propname)
        filter_name = self.filter_name.lower()

        flt_flags = [
            self.bitflag_filter_item
            if (item.type == globs.CL_MATERIAL and filter_name in item.mat.name.lower()) or item.type == globs.CL_OBJECT
            else 0
            for item in data
        ]

        flt_neworder = self._filter_by_names(data) if self.use_filter_sort_alpha else []
        return flt_flags, flt_neworder

    @staticmethod
    def _filter_by_names(data: SMCObData) -> List[int]:
        sorted_items = sorted(enumerate(data), key=lambda x: x[1].mat.name if x[1].type == globs.CL_MATERIAL else '')
        sorted_pairs = sorted(enumerate(sorted_items), key=lambda x: x[1])
        return [x[0] for x in sorted_pairs]
