from typing import DefaultDict
from typing import Dict
from typing import List
from typing import NewType
from typing import Tuple
from typing import Union

import bpy
from mathutils import Vector

from . import globs

BlClasses = NewType(
    'BlClasses',
    Union[bpy.types.Panel, bpy.types.Operator, bpy.types.PropertyGroup, bpy.types.AddonPreferences, bpy.types.UIList]
)

SMCIcons = NewType('SMCIcons', Union[bpy.utils.previews.ImagePreviewCollection, None])

Scene = bpy.types.ViewLayer if globs.is_blender_2_80_or_newer else bpy.types.Scene
SMCObDataItem = NewType('SMCObDataItem', Dict[bpy.types.Material, int])
SMCObData = NewType('SMCObData', SMCObDataItem)
MatsUV = Dict[str, DefaultDict[bpy.types.Material, List[Vector]]]
StructureItem = Dict[str, Union[List, Dict[str, Union[Dict[str, int], Tuple, str, None]]]]
Structure = Dict[bpy.types.Material, StructureItem]
ObMats = NewType('ObMats', Union[bpy.types.bpy_prop_collection, List[bpy.types.Material]])
CombMats = NewType('CombMats', Dict[int, bpy.types.Material])

MatDict = NewType('MatDict', DefaultDict[Tuple, List[bpy.types.Material]])
Diffuse = NewType('Diffuse', Union[bpy.types.bpy_prop_collection, Tuple[float, float, float]])
