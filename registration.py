from typing import Dict, Union

import bpy

from . import addon_updater_ops, extend_lists, extend_types, globs, operators, ui
from .icons import initialize_smc_icons, unload_smc_icons
from .type_annotations import BlClasses

__bl_classes = [
    ui.credits_menu.CreditsMenu,
    ui.main_menu.MaterialMenu,
    ui.property_menu.PropertyMenu,
    ui.update_menu.UpdateMenu,

    operators.combiner.Combiner,
    operators.combine_list.RefreshObData,
    operators.combine_list.CombineSwitch,
    operators.browser.OpenBrowser,
    operators.get_pillow.InstallPIL,

    extend_types.CombineListEntry,
    extend_types.UpdatePreferences,

    extend_lists.SMC_UL_Combine_List,
]


def register_all(bl_info: Dict[str, Union[str, tuple]]) -> None:
    _register_classes()
    initialize_smc_icons()
    addon_updater_ops.register(bl_info)
    addon_updater_ops.check_for_update_background()
    extend_types.register()


def unregister_all() -> None:
    _unregister_classes()
    unload_smc_icons()
    addon_updater_ops.unregister()
    extend_types.unregister()


def _register_classes() -> None:
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
    count = 0
    for cls in reversed(__bl_classes):
        try:
            bpy.utils.unregister_class(cls)
            count += 1
        except (ValueError, RuntimeError) as e:
            print('Error:', cls, e)
    print('Unregistered', count, 'Material Combiner classes.')


def make_annotations(cls: BlClasses) -> BlClasses:
    if globs.is_blender_2_79_or_older:
        return cls

    if bpy.app.version >= (2, 93, 0):
        bl_props = {k: v for k, v in cls.__dict__.items() if isinstance(v, bpy.props._PropertyDeferred)}
    else:
        bl_props = {k: v for k, v in cls.__dict__.items() if isinstance(v, tuple)}

    if bl_props:
        if '__annotations__' not in cls.__dict__:
            setattr(cls, '__annotations__', {})

        annotations = cls.__dict__['__annotations__']

        for k, v in bl_props.items():
            annotations[k] = v
            delattr(cls, k)

    return cls
