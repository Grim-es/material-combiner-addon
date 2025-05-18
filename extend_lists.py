"""UI list implementation for the Material Combiner addon.

This module provides the custom UIList implementation used in the Material Combiner
addon, handling display, filtering, and sorting of objects and materials in the
combine list. It maintains a proper hierarchical structure between objects and
their materials during filtering and sorting operations.
"""

from typing import Any, Dict, List, Tuple

import bpy
from bpy.props import BoolProperty, EnumProperty, StringProperty

from .globs import (
    ICON_DROPDOWN,
    ICON_OBJECT,
    ICON_PROPERTIES,
    CombineListTypes,
    is_blender_modern,
)


class SMC_UL_Combine_List(bpy.types.UIList):
    """Custom UI list for displaying materials and objects in the Material Combiner.

    This UIList implementation displays a hierarchical list of objects and their
    materials with visual indicators for selection state, supports custom filtering
    and sorting options, and maintains parent-child relationships during filtering.
    """

    filter_name = StringProperty(
        name='Filter',
        default='',
        description='Filter items by name',
    )
    filter_mode = EnumProperty(
        name='Filter Mode',
        items=[
            ('MATERIAL', 'Material', 'Filter by material name'),
            ('OBJECT', 'Object', 'Filter by object name'),
            ('BOTH', 'Both', 'Filter by both material and object name'),
        ],
        default='BOTH',
        description='Choose how filtering is applied'
    )
    use_filter_sort_reverse = BoolProperty(
        name='Reverse Sort',
        default=False,
        description='Reverse the order of shown items'
    )
    filter_initialized = BoolProperty(
        name='Filter Initialized',
        default=False,
        description='Whether the filter panel has been initialized'
    )

    def draw_item(self, context: bpy.types.Context, layout: bpy.types.UILayout, data: Any,  # noqa: PLR0913
                  item: Any, icon: int, active_data: Any,
                  active_propname: str, index: int = 0,
                  filter_flag: int = 0) -> None:
        """Draw an individual list item with context-sensitive UI elements.

        This method renders either an object entry or a material entry
        based on the item type, with appropriate controls for each.

        Args:
            context: The current Blender context.
            layout: The layout to draw the item in.
            data: The data containing the collection property.
            item: The item to draw.
            icon: The icon to use for the item.
            active_data: The data containing the active property.
            active_propname: The name of the active property.
            index: The index of the item in the list.
            filter_flag: The filter flag for the item.
        """
        if not self.filter_initialized:
            self.use_filter_show = True
            self.filter_initialized = True

        row = layout.row(align=True)

        if item.type == CombineListTypes.OBJECT:
            self._draw_object_entry(row, item, index)
        elif item.type == CombineListTypes.MATERIAL:
            self._draw_material_entry(row, item, index)

    @staticmethod
    def _draw_object_entry(row: bpy.types.UILayout, item: Any, index: int) -> None:
        """Render an object list entry with appropriate selection controls.

        Creates a row with the object name and a button to select/deselect
        all materials belonging to this object.

        Args:
            row: The row layout to draw into.
            item: The object item to display.
            index: The index of the item in the list.
        """
        row.prop(item.ob, 'name', text='', icon=ICON_OBJECT, emboss=False)

        action_row = row.row(align=True)
        action_row.alignment = 'RIGHT'
        action_label = 'Deselect All' if item.used else 'Select All'
        action_row.operator('smc.combine_switch', text=action_label, emboss=False).list_id = index

    def _draw_material_entry(self, row: bpy.types.UILayout, item: Any, index: int) -> None:
        """Render a material list entry with preview and settings controls.

        Creates a row with material preview, name, layer selection,
        enable/disable toggle, and settings button.

        Args:
            row: The row layout to draw into.
            item: The material item to display.
            index: The index of the item in the list.
        """
        if is_blender_modern:
            row.separator(factor=1.5)
        else:
            row.separator()

        self._draw_toggle_control(row, item, index)

        preview_id = self._get_material_preview_id(item)
        row.label(text='', icon_value=preview_id)
        row.prop(item.mat, 'name', text='', emboss=False)

        self._draw_layer_control(row, item)
        self._draw_settings_control(row, index)

    @staticmethod
    def _get_material_preview_id(item: Any) -> int:
        """Get the material preview icon ID with fallback handling.

        Returns the material's preview icon ID if available,
        or a fallback question mark icon if not.

        Args:
            item: The material item to get the preview for.

        Returns:
            Icon ID for the material preview or fallback icon.
        """
        if item.mat and item.mat.preview:
            return item.mat.preview.icon_id
        return bpy.context.icon(bpy.context, 'QUESTION')

    @staticmethod
    def _draw_layer_control(layout: bpy.types.UILayout, item: Any) -> None:
        """Render the layer number input column for a material.

        Creates a narrow column with a numeric input for the layer number,
        which determines which atlas the material will be added to.

        Args:
            layout: The layout to draw into.
            item: The material item to draw the layer control for.
        """
        col = layout.column(align=True)
        col.scale_x = 0.4
        col.prop(item, 'layer', text='')

    @staticmethod
    def _draw_toggle_control(layout: bpy.types.UILayout, item: Any, index: int) -> None:
        """Render the material toggle button with the appropriate icon.

        Creates a button to toggle the material's inclusion in the atlas,
        with an icon indicating the current state.

        Args:
            layout: The layout to draw into.
            item: The material item to draw the toggle for.
            index: The index of the item in the list.
        """
        icon = 'CHECKBOX_HLT' if item.used else 'CHECKBOX_DEHLT'
        layout.operator('smc.combine_switch', text='', icon=icon, emboss=False).list_id = index

    @staticmethod
    def _draw_settings_control(layout: bpy.types.UILayout, index: int) -> None:
        """Render the material properties button.

        Creates a button that opens the material properties dialog
        for configuring additional material settings.

        Args:
            layout: The layout to draw into.
            index: The index of the item in the list.
        """
        layout.operator('smc.material_properties', text='', icon=ICON_PROPERTIES).list_id = index

    def draw_filter(self, context: bpy.types.Context, layout: bpy.types.UILayout) -> None:
        """Draw the filter panel with filtering and sorting controls.

        Creates a filter input field and buttons for controlling
        filter mode and sort order.

        Args:
            context: The current Blender context.
            layout: The layout to draw the filter panel in.
        """
        row = layout.row(align=True)
        row.prop(self, 'filter_name', text='')

        filter_mode_icon = self._get_filter_mode_icon()
        row.prop_menu_enum(self, 'filter_mode', text='', icon=filter_mode_icon)

        sort_reverse_icon = 'TRIA_DOWN' if self.use_filter_sort_reverse else 'TRIA_UP'
        row.prop(self, 'use_filter_sort_reverse', icon=sort_reverse_icon, icon_only=True)
        row.menu("SMC_MT_SelectionMenu", text="", icon=ICON_DROPDOWN)

    def _get_filter_mode_icon(self) -> str:
        """Get the appropriate icon name for the current filter mode.

        Returns an icon name that visually represents the current
        filter mode (material, object, or both).

        Returns:
            Icon name string corresponding to the current filter mode.
        """
        if self.filter_mode == 'MATERIAL':
            return 'MATERIAL'
        elif self.filter_mode == 'OBJECT':
            return 'OBJECT_DATA'
        else:
            return 'FILTER'

    def filter_items(self, context: bpy.types.Context, data: Any, propname: str) -> Tuple[List[int], List[int]]:
        """Filter and sort combine list items based on current filter settings.

        Implements complex filtering and sorting logic that maintains the
        hierarchical structure between objects and their materials. Handles
        grouping, filtering by name, and customized sorting.

        Args:
            context: The current Blender context.
            data: The data containing the collection property.
            propname: The name of the collection property.

        Returns:
            A tuple containing filter flags and new order indices.
        """
        collection = getattr(data, propname)
        total_items = len(collection)
        filter_flags = [self.bitflag_filter_item] * total_items

        # Build a list of (original_index, item) tuples.
        items_with_indices = list(enumerate(collection))

        # Group items by ob_id.
        groups = self._group_items_by_ob_id(items_with_indices)

        # Apply filtering per group if a filter text is provided.
        if self.filter_name:
            filter_text = self.filter_name.lower()
            for group in groups.values():
                if self.filter_mode == 'OBJECT':
                    self._apply_filter_by_object(group, filter_text, filter_flags)
                elif self.filter_mode == 'MATERIAL':
                    self._apply_filter_by_material(group, filter_text, filter_flags)
                elif self.filter_mode == 'BOTH':
                    self._apply_filter_both(group, filter_text, filter_flags)

        # Sort group keys (ob_ids) based on the OBJECT name.
        sorted_group_ids = sorted(
            groups.keys(),
            key=lambda ob_index: self._get_object_name_for_group(groups[ob_index]),
            reverse=self.use_filter_sort_reverse
        )

        # Build the desired order by processing each group.
        desired_order = []
        for ob_id in sorted_group_ids:
            group_items = groups[ob_id]
            group_order = self._sort_group_items(group_items, reverse_sort=self.use_filter_sort_reverse)
            desired_order.extend(group_order)

        # IMPORTANT: Do not reverse the entire order here.
        new_order = desired_order

        # Build mapping: original index -> new order position.
        filter_neworder = [0] * total_items
        for new_idx, orig_idx in enumerate(new_order):
            filter_neworder[orig_idx] = new_idx

        return filter_flags, filter_neworder

    @staticmethod
    def _group_items_by_ob_id(
            items_with_indices: List[Tuple[int, bpy.types.PropertyGroup]]
    ) -> Dict[int, List[Tuple[int, bpy.types.PropertyGroup]]]:
        """Group list items by their object ID.

        Creates a dictionary mapping object IDs to lists of items
        belonging to those objects, preserving the original indices.

        Args:
            items_with_indices: List of tuples containing (original_index, item).

        Returns:
            Dictionary mapping object IDs to lists of (original_index, item) tuples.
        """
        groups = {}
        for index, item in items_with_indices:
            groups.setdefault(item.ob_id, []).append((index, item))
        return groups

    def _apply_filter_by_object(
            self,
            group: List[Tuple[int, bpy.types.PropertyGroup]],
            filter_text: str,
            filter_flags: List[int]
    ) -> None:
        """Apply filtering based on object names.

        Shows or hides entire groups based on whether the object name
        matches the filter text.

        Args:
            group: List of (original_index, item) tuples for a group.
            filter_text: The text to filter by (lowercase).
            filter_flags: List of filter flags to modify.
        """
        object_match = False
        for _, item in group:
            if item.type == CombineListTypes.OBJECT and item.ob:
                if filter_text in item.ob.name.lower():
                    object_match = True
                break
        flag = self.bitflag_filter_item if object_match else 0
        for idx, _ in group:
            filter_flags[idx] = flag

    def _apply_filter_by_material(
            self,
            group: List[Tuple[int, bpy.types.PropertyGroup]],
            filter_text: str,
            filter_flags: List[int]
    ) -> None:
        """Apply filtering based on material names.

        Shows only materials matching the filter text, and ensures
        their parent objects remain visible.

        Args:
            group: List of (original_index, item) tuples for a group.
            filter_text: The text to filter by (lowercase).
            filter_flags: List of filter flags to modify.
        """
        material_found = False
        # First pass: mark MATERIAL items.
        for idx, item in group:
            if item.type == CombineListTypes.MATERIAL:
                if item.mat and filter_text in item.mat.name.lower():
                    filter_flags[idx] = self.bitflag_filter_item
                    material_found = True
                else:
                    filter_flags[idx] = 0
            else:
                filter_flags[idx] = 0
        # Second pass: if any MATERIAL matched, show OBJECT and SEPARATOR items.
        if material_found:
            for idx, item in group:
                if item.type in (CombineListTypes.OBJECT, CombineListTypes.SEPARATOR):
                    filter_flags[idx] = self.bitflag_filter_item

    def _apply_filter_both(
            self,
            group: List[Tuple[int, bpy.types.PropertyGroup]],
            filter_text: str,
            filter_flags: List[int]
    ) -> None:
        """Apply filtering based on both object and material names.

        Shows entire groups if the object name matches, or shows only
        matching materials with their parent objects otherwise.

        Args:
            group: List of (original_index, item) tuples for a group.
            filter_text: The text to filter by (lowercase).
            filter_flags: List of filter flags to modify.
        """
        object_matches = any(
            filter_text in (item.ob.name.lower() if item.ob else "")
            for _, item in group if item.type == CombineListTypes.OBJECT
        )
        if object_matches:
            for idx, _ in group:
                filter_flags[idx] = self.bitflag_filter_item
            return

        material_found = False
        for idx, item in group:
            if item.type == CombineListTypes.MATERIAL:
                if item.mat and filter_text in item.mat.name.lower():
                    filter_flags[idx] = self.bitflag_filter_item
                    material_found = True
                else:
                    filter_flags[idx] = 0
            elif item.type in (CombineListTypes.OBJECT, CombineListTypes.SEPARATOR):
                filter_flags[idx] = 0
        if material_found:
            for idx, item in group:
                if item.type in (CombineListTypes.OBJECT, CombineListTypes.SEPARATOR):
                    filter_flags[idx] = self.bitflag_filter_item

    @staticmethod
    def _get_object_name_for_group(group: List[Tuple[int, bpy.types.PropertyGroup]]) -> str:
        """Get the object name for a group of items.

        Retrieves the name of the object for sorting purposes.

        Args:
            group: List of (original_index, item) tuples for a group.

        Returns:
            Lowercase object name or empty string if not found.
        """
        for _, item in group:
            if item.type == CombineListTypes.OBJECT and item.ob:
                return item.ob.name.lower()
        return ''

    @staticmethod
    def _sort_group_items(group: List[Tuple[int, bpy.types.PropertyGroup]], reverse_sort: bool) -> List[int]:
        """Sort items within a group maintaining hierarchical structure.

        Sorts objects first, then materials, and finally separators,
        respecting the hierarchical relationship between them.

        Args:
            group: List of (original_index, item) tuples for a group.
            reverse_sort: Whether to sort in reverse order.

        Returns:
            List of original indices in the desired sort order.
        """
        object_entries = [(idx, item) for idx, item in group if item.type == CombineListTypes.OBJECT]
        material_entries = [(idx, item) for idx, item in group if item.type == CombineListTypes.MATERIAL]
        separator_entries = [(idx, item) for idx, item in group if item.type == CombineListTypes.SEPARATOR]

        object_entries.sort(
            key=lambda pair: pair[1].ob.name.lower() if pair[1].ob else '',
            reverse=reverse_sort
        )
        material_entries.sort(
            key=lambda pair: pair[1].mat.name.lower() if pair[1].mat else '',
            reverse=reverse_sort
        )

        # Always keep SEPARATOR entries at the end.
        sorted_group = object_entries + material_entries + separator_entries
        return [idx for idx, _ in sorted_group]
