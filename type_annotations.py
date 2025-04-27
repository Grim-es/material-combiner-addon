"""Type annotations for the Material Combiner addon.

This module defines custom type hints used throughout the addon to improve
code readability, maintainability, and IDE support. It centralizes complex
type definitions to avoid repetition and ensure consistency.
"""

from typing import DefaultDict, Dict, List, Tuple, Union

import bpy
from mathutils import Vector

from . import globs

# Blender class types that can be registered
BlClasses = Union[
    bpy.types.Panel,
    bpy.types.Operator,
    bpy.types.PropertyGroup,
    bpy.types.AddonPreferences,
    bpy.types.UIList,
]

# Type for the icon preview collection system
SMCIcons = Union[
    bpy.utils.previews.ImagePreviewCollection,
    Dict[str, bpy.types.ImagePreview],
    None,
]

# Scene type that handles version differences
Scene = bpy.types.ViewLayer if globs.is_blender_modern else bpy.types.Scene

# Object data structure for material mapping
SMCObDataItem = Dict[bpy.types.Material, int]
SMCObData = Dict[str, SMCObDataItem]

# Materials to a UV mapping type
MatsUV = Dict[str, DefaultDict[bpy.types.Material, List[Vector]]]

# Atlas structure item definitions
StructureItem = Dict[
    str,
    Union[
        List,
        Dict[str, Union[Dict[str, int], Tuple, bpy.types.PackedFile, None]],
    ],
]
Structure = Dict[bpy.types.Material, StructureItem]

# Object materials collection type
ObMats = Union[bpy.types.bpy_prop_collection, List[bpy.types.Material]]

# Combined materials mapping by layer index
CombMats = Dict[int, bpy.types.Material]

# Material grouping for duplicate detection
MatDictItem = List[bpy.types.Material]
MatDict = DefaultDict[Tuple, MatDictItem]

# UI list data structure for combine panel
CombineListDataMat = Dict[str, Union[int, bool]]
CombineListDataItem = Dict[
    str, Union[Dict[bpy.types.Material, CombineListDataMat], bool]
]
CombineListData = Dict[bpy.types.Object, CombineListDataItem]

# Material diffuse color representation across Blender versions
Diffuse = Union[
    bpy.types.bpy_prop_collection,
    Tuple[float, float, float],
    Tuple[int, int, int],
]
