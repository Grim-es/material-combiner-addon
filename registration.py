import bpy
from . icons import initialize_smc_icons, unload_smc_icons
from . import addon_updater_ops

from . import ui
from . import operators
from . import extend_types
from . import extend_lists

__bl_classes = [
    ui.credits_menu.CreditsMenu,
    ui.main_menu.MaterialMenu,
    ui.properties_menu.PropertiesMenu,
    ui.update_menu.UpdateMenu,

    operators.combiner.Combiner,
    operators.combine_list.RefreshObData,
    operators.combine_list.CombineSwitch,
    operators.multicombine_list.MultiCombineColor,
    operators.multicombine_list.MultiCombineImageAdd,
    operators.multicombine_list.MultiCombineImageMove,
    operators.multicombine_list.MultiCombineImagePath,
    operators.multicombine_list.MultiCombineImageReset,
    operators.multicombine_list.MultiCombineImageRemove,
    operators.browser.OpenBrowser,
    operators.get_pillow.InstallPIL,

    extend_types.CombineList,
    extend_types.UpdatePreferences,

    extend_lists.SMC_UL_Combine_List,
]


def register_all(bl_info):
    register_classes()
    initialize_smc_icons()
    addon_updater_ops.register(bl_info)
    extend_types.register()


def unregister_all():
    unregister_classes()
    unload_smc_icons()
    addon_updater_ops.unregister()
    extend_types.unregister()


def register_classes():
    count = 0
    for cls in __bl_classes:
        make_annotations(cls)
        try:
            bpy.utils.register_class(cls)
            count += 1
        except ValueError as e:
            print('Error:', cls, e)
            pass
    print('Registered', count, 'Material Combiner classes.')
    if count < len(__bl_classes):
        print('Skipped', len(__bl_classes) - count, 'Material Combiner classes.')


def unregister_classes():
    count = 0
    for cls in reversed(__bl_classes):
        try:
            bpy.utils.unregister_class(cls)
            count += 1
        except ValueError:
            pass
        except RuntimeError:
            pass
    print('Unregistered', count, 'Material Combiner classes.')


def make_annotations(cls):
    if bpy.app.version >= (2, 80, 0):
        bl_props = {k: v for k, v in cls.__dict__.items() if isinstance(v, tuple)}
        if bl_props:
            if '__annotations__' not in cls.__dict__:
                setattr(cls, '__annotations__', {})
            annotations = cls.__dict__['__annotations__']
            for k, v in bl_props.items():
                annotations[k] = v
                delattr(cls, k)
    return cls

