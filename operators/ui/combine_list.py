"""Material list management for the Material Combiner addon.

This module provides operators for managing the material list used in the combining
process. It includes functionality for refreshing the list, toggling selection
states, and managing selection of materials and objects.

Usage example:
    bpy.ops.smc.refresh_ob_data()
    bpy.ops.smc.combine_switch(list_id=index)
    bpy.ops.smc.select_all()
    bpy.ops.smc.select_none()
"""

from collections import defaultdict
from typing import Dict, List, Set, cast

import bpy
from bpy.props import IntProperty

from ...globs import CombineListTypes, is_blender_3_plus
from ...type_annotations import CombineListData, Scene
from ...utils.materials import get_materials


class MaterialListRefreshOperator(bpy.types.Operator):
    """Updates the material list for combining.

    Scans visible mesh objects with UV maps and materials, rebuilding the combine
    list while preserving user selections from previous refreshes.
    """

    bl_idname = "smc.refresh_ob_data"
    bl_label = "Update Material List"
    bl_description = "Rebuilds the list of available materials for combining"

    def execute(self, context: bpy.types.Context) -> Set[str]:
        """Execute the operator to refresh the object and material list.

        Args:
            context: Current Blender context.

        Returns:
            Set containing the result status.
        """
        scene = context.scene
        visible_objects = self._get_eligible_objects(context)
        previous_state = self._cache_previous_selections(scene)
        self._rebuild_material_list(scene, visible_objects, previous_state)
        return {"FINISHED"}

    @staticmethod
    def _get_eligible_objects(
        context: bpy.types.Context,
    ) -> Set[bpy.types.Object]:
        """Retrieve valid objects for material processing.

        Finds mesh objects that have both an active UV layer and materials.

        Args:
            context: Current Blender context.

        Returns:
            Set of eligible objects for material combining.
        """
        return {
            obj
            for obj in context.visible_objects
            if (
                obj.type == "MESH"
                and obj.data.uv_layers.active
                and obj.data.materials
            )
        }

    def _cache_previous_selections(self, scene: Scene) -> CombineListData:
        """Preserve previous user selections before rebuilding.

        Creates a cached copy of the current material selections to ensure
        user choices are preserved during list refresh.

        Args:
            scene: Current Blender scene.

        Returns:
            Dictionary containing cached selection data.
        """
        cached_data = cast(
            CombineListData, defaultdict(self._create_object_entry)
        )

        for item in scene.smc_ob_data:
            if item.type == CombineListTypes.OBJECT:
                cached_data[item.ob]["used"] = item.used
            elif item.type == CombineListTypes.MATERIAL:
                mat_entry = cached_data[item.ob]["materials"][item.mat]
                mat_entry.update({"used": item.used, "layer": item.layer})

        return cached_data

    def _rebuild_material_list(
        self,
        scene: Scene,
        objects: Set[bpy.types.Object],
        cached_data: CombineListData,
    ) -> None:
        """Recreate the material list from the current scene state.

        Builds a new list of objects and materials based on the current scene,
        preserving selection states from the cached data.

        Args:
            scene: Current Blender scene.
            objects: Set of eligible objects to process.
            cached_data: Dictionary containing cached selection data.
        """
        scene.smc_ob_data.clear()

        for obj_id, obj in enumerate(objects):
            obj_state = cached_data[obj]
            self._add_object_entry(scene, obj, obj_id, obj_state["used"])
            self._process_object_materials(scene, obj, obj_id, obj_state)
            self._add_list_separator(scene, obj_id)

    def _process_object_materials(
        self, scene: Scene, obj: bpy.types.Object, obj_id: int, obj_state: Dict
    ) -> None:
        """Handle material entries for a single object.

        Processes all materials for the given object and adds them to the list.

        Args:
            scene: Current Blender scene.
            obj: Object being processed.
            obj_id: Index of the object in the list.
            obj_state: Dictionary containing the object's cached state.
        """
        for material in get_materials(obj):
            self._ensure_material_preview(material)
            mat_state = obj_state["materials"][material]
            self._add_material_entry(
                scene,
                obj,
                obj_id,
                material,
                mat_state["used"],
                mat_state["layer"],
            )

    @staticmethod
    def _ensure_material_preview(material: bpy.types.Material) -> None:
        """Generate preview if missing in Blender 3.0+.

        Args:
            material: Material to ensure preview for.
        """
        if is_blender_3_plus and not material.preview:
            material.preview_ensure()

    @staticmethod
    def _create_object_entry() -> Dict:
        """Create the default structure for object cache entries.

        Returns:
            Dictionary with default values for a new object entry.
        """
        return {
            "used": True,
            "materials": defaultdict(lambda: {"used": True, "layer": 1}),
        }

    @staticmethod
    def _add_object_entry(
        scene: Scene, obj: bpy.types.Object, obj_id: int, is_used: bool
    ) -> None:
        """Create new object entry in the list.

        Args:
            scene: Current Blender scene.
            obj: Object to add to the list.
            obj_id: Index of the object in the list.
            is_used: Whether the object is selected for combining.
        """
        entry = scene.smc_ob_data.add()
        entry.ob = obj
        entry.ob_id = obj_id
        entry.type = CombineListTypes.OBJECT
        entry.used = is_used

    @staticmethod
    def _add_material_entry(  # noqa: PLR0913
        scene: Scene,
        obj: bpy.types.Object,
        obj_id: int,
        material: bpy.types.Material,
        is_used: bool,
        layer: int,
    ) -> None:
        """Create new material entry in the list.

        Args:
            scene: Current Blender scene.
            obj: Object the material belongs to.
            obj_id: Index of the object in the list.
            material: Material to add to the list.
            is_used: Whether the material is selected for combining.
            layer: Atlas layer assignment for the material.
        """
        entry = scene.smc_ob_data.add()
        entry.ob = obj
        entry.ob_id = obj_id
        entry.mat = material
        entry.type = CombineListTypes.MATERIAL
        entry.used = is_used
        entry.layer = layer

    @staticmethod
    def _add_list_separator(scene: Scene, obj_id: int) -> None:
        """Add visual separator between objects in the list.

        Args:
            scene: Current Blender scene.
            obj_id: Index of the object to add separator after.
        """
        entry = scene.smc_ob_data.add()
        entry.type = CombineListTypes.SEPARATOR
        entry.ob_id = obj_id


class MaterialListToggleOperator(bpy.types.Operator):
    """Toggle selection states in the material list.

    Provides functionality to toggle the selection state of materials and objects
    in the combining list, handling parent-child relationships between objects
    and their materials.
    """

    bl_idname = "smc.combine_switch"
    bl_label = "Toggle Selection"
    bl_description = "Toggle selection of materials/objects for combining"

    list_id = IntProperty(name="List Index", default=0)

    def execute(self, context: bpy.types.Context) -> Set[str]:
        """Main execution method for toggle operation.

        Args:
            context: Current Blender context.

        Returns:
            Set containing operation status.
        """
        scene = context.scene
        items = scene.smc_ob_data
        target_item = items[self.list_id]

        if target_item.type == CombineListTypes.OBJECT:
            self._toggle_object_state(items, target_item)
        elif target_item.type == CombineListTypes.MATERIAL:
            self._toggle_material_state(items, target_item)

        return {"FINISHED"}

    @staticmethod
    def _toggle_object_state(
        items: List[bpy.types.PropertyGroup],
        target_item: bpy.types.PropertyGroup,
    ) -> None:
        """Toggle selection state for an object and its materials.

        When toggling an object, all its materials are also toggled to match.

        Args:
            items: List of all items in the combine list.
            target_item: The object item being toggled.
        """
        materials = [
            item
            for item in items
            if item.ob_id == target_item.ob_id
            and item.type == CombineListTypes.MATERIAL
        ]

        if not materials:
            return

        new_state = not target_item.used
        target_item.used = new_state
        for mat_item in materials:
            mat_item.used = new_state

    @staticmethod
    def _toggle_material_state(
        items: List[bpy.types.PropertyGroup],
        target_item: bpy.types.PropertyGroup,
    ) -> None:
        """Toggle selection state for a single material.

        When enabling a material, its parent object is automatically enabled.

        Args:
            items: List of all items in the combine list.
            target_item: The material item being toggled.
        """
        parent_object = next(
            (
                item
                for item in items
                if item.ob_id == target_item.ob_id
                and item.type == CombineListTypes.OBJECT
            ),
            None,
        )

        if parent_object and not target_item.used:
            parent_object.used = True

        target_item.used = not target_item.used


class SelectAllMaterials(bpy.types.Operator):
    """Select all materials in the combine list.

    Operator that marks all objects and materials as selected for the combining
    process.
    """

    bl_idname = "smc.select_all"
    bl_label = "Select All"
    bl_description = "Select all objects and materials"

    def execute(self, context: bpy.types.Context) -> Set[str]:
        """Select all objects and materials in the combine list.

        Args:
            context: Current Blender context.

        Returns:
            Set containing operation status.
        """
        for item in context.scene.smc_ob_data:
            if item.type in (
                CombineListTypes.OBJECT,
                CombineListTypes.MATERIAL,
            ):
                item.used = True
        return {"FINISHED"}


class SelectNoneMaterials(bpy.types.Operator):
    """Deselect all materials in the combine list.

    Operator that marks all objects and materials as deselected, excluding them
    from the combining process.
    """

    bl_idname = "smc.select_none"
    bl_label = "Select None"
    bl_description = "Deselect all objects and materials"

    def execute(self, context: bpy.types.Context) -> Set[str]:
        """Deselect all objects and materials in the combine list.

        Args:
            context: Current Blender context.

        Returns:
            Set containing operation status.
        """
        for item in context.scene.smc_ob_data:
            if item.type in (CombineListTypes.OBJECT, CombineListTypes.MATERIAL):
                item.used = False
        return {'FINISHED'}
