"""Registration module for the Material Combiner addon.

This module handles the registration and unregistration of all Blender classes
used by the addon. It also manages version-specific property annotations and
initializes the icon system and updater functionality.
"""

from typing import Dict, Union

import bpy

from . import (
    addon_updater_ops,
    extend_lists,
    extend_types,
    globs,
    operators,
    ui,
)
from .icons import initialize_smc_icons, unload_smc_icons
from .type_annotations import BlClasses

__bl_classes = [
    ui.selection_menu.SMC_MT_SelectionMenu,

    ui.credits_panel.CreditsPanel,
    ui.main_panel.MaterialCombinerPanel,
    ui.property_panel.PropertyMenu,
    ui.update_panel.UpdatePanel,

    operators.browser.OpenBrowser,
    operators.combine_list.MaterialListRefreshOperator,
    operators.combine_list.MaterialListToggleOperator,
    operators.combine_list.SelectAllMaterials,
    operators.combine_list.SelectNoneMaterials,
    operators.combiner.Combiner,
    operators.get_pillow.InstallPIL,

    extend_types.CombineListEntry,
    extend_types.UpdatePreferences,

    extend_lists.SMC_UL_Combine_List,
]


def register_all(bl_info: Dict[str, Union[str, tuple]]) -> None:
    """Register all components of the addon.
    
    This is the main registration function called when the addon is enabled.
    It registers all classes, initializes icons, and sets up the updater.
    
    Args:
        bl_info: Dictionary containing addon metadata
    """
    _register_classes()
    initialize_smc_icons()
    addon_updater_ops.register(bl_info)
    addon_updater_ops.check_for_update_background()
    extend_types.register()


def unregister_all() -> None:
    """Unregister all components of the addon.
    
    This is the main unregistration function called when the addon is disabled.
    It unregisters all classes, cleans up icons, and shuts down the updater.
    """
    _unregister_classes()
    unload_smc_icons()
    addon_updater_ops.unregister()
    extend_types.unregister()


def _register_classes() -> None:
    """Register all Blender classes used by the addon.
    
    Converts properties to annotations as needed and logs registration results.
    """
    count = 0
    for cls in __bl_classes:
        make_annotations(cls)
        try:
            bpy.utils.register_class(cls)
            count += 1
        except ValueError as e:
            print('Error:', cls, e)
    print('Registered', count, 'Material Combiner classes.')
    if count < len(__bl_classes):
        print('Skipped', len(__bl_classes) - count, 'Material Combiner classes.')


def _unregister_classes() -> None:
    """Unregister all Blender classes used by the addon.
    
    Classes are unregistered in reverse order to handle dependencies.
    """
    count = 0
    for cls in reversed(__bl_classes):
        try:
            bpy.utils.unregister_class(cls)
            count += 1
        except (ValueError, RuntimeError) as e:
            print('Error:', cls, e)
    print('Unregistered', count, 'Material Combiner classes.')


def make_annotations(cls: BlClasses) -> BlClasses:
    """Convert class properties to annotations for Blender 2.80+.
    
    This function handles the transition from Blender's old property 
    definition system to the new annotation-based system.
    
    Args:
        cls: Blender class to process
        
    Returns:
        The processed class with properties converted to annotations
    """
    if globs.is_blender_legacy:
        return cls

    if bpy.app.version >= (2, 93, 0):
        bl_props = {k: v for k, v in cls.__dict__.items() if isinstance(v, bpy.props._PropertyDeferred)}
    else:
        bl_props = {k: v for k, v in cls.__dict__.items() if isinstance(v, tuple)}

    if bl_props:
        if '__annotations__' not in cls.__dict__:
            cls.__annotations__ = {}

        annotations = cls.__dict__['__annotations__']

        for k, v in bl_props.items():
            annotations[k] = v
            delattr(cls, k)

    return cls
