import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)

from . import addon_updater_ops

_SCENE_PROPS = (
    'smc_ob_data', 'smc_ob_data_id', 'smc_list_id', 'smc_size',
    'smc_size_width', 'smc_size_height', 'smc_crop', 'smc_pixel_art',
    'smc_diffuse_size', 'smc_gaps', 'smc_save_path'
)

_MATERIAL_PROPS = (
    'root_mat', 'smc_diffuse', 'smc_size',
    'smc_size_width', 'smc_size_height'
)

_DEFAULT_ATLAS_SIZE = 'QUAD'
_DEFAULT_DIMENSION = 4096
_MIN_DIMENSION = 8
_MAX_DIMENSION = 8192

_ATLAS_SIZE_ITEMS = [
    ('PO2', 'Power of 2', 'Combined image size is power of 2'),
    ('QUAD', 'Quadratic', 'Combined image has same width and height'),
    ('AUTO', 'Automatic', 'Combined image has minimal size'),
    ('CUST', 'Custom', 'Proportionally scaled to fit custom size'),
    ('STRICTCUST', 'Strict Custom', 'Exact custom width and height'),
]


class CombineListEntry(bpy.types.PropertyGroup):
    ob = PointerProperty(
        name='Object',
        type=bpy.types.Object,
        description='Source object containing materials'
    )

    ob_id = IntProperty(
        name='Object ID',
        default=0,
        description='Unique identifier for tracking objects in the list'
    )

    mat = PointerProperty(
        name='Material',
        type=bpy.types.Material,
        description='Material instance to combine'
    )

    layer = IntProperty(
        name='Layer Group',
        min=1,
        max=99,
        step=1,
        default=1,
        description='Materials with the same layer number will be merged\n'
                    'Use to create multiple materials linked to the same atlas'
    )

    used = BoolProperty(
        name='Include',
        default=True,
        description='Include this element in the atlas generation'
    )

    type = IntProperty(
        name='Entry Type',
        default=0,
        description='0 = Object, 1 = Material'
    )


class UpdatePreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    auto_check_update = BoolProperty(
        name='Automatic Update Checks',
        default=True,
        description='Enable automatic update checks at specified intervals'
    )

    updater_interval_months = bpy.props.IntProperty(
        name='Months',
        default=0,
        min=0,
        description='Monthly interval between update checks'
    )

    updater_interval_days = IntProperty(
        name='Days',
        default=1,
        min=1,
        description='Daily interval between update checks'
    )

    updater_interval_hours = IntProperty(
        name='Hours',
        default=0,
        min=0,
        max=0,
        description='Hourly interval between update checks'
    )

    updater_interval_minutes = IntProperty(
        name='Minutes',
        default=0,
        min=0,
        max=0,
        description='Minute interval between update checks'
    )

    def draw(self, context: bpy.types.Context):
        addon_updater_ops.update_settings_ui(self, context)


def _register_scene_properties() -> None:
    bpy.types.Scene.smc_ob_data = CollectionProperty(
        type=CombineListEntry
    )
    bpy.types.Scene.smc_ob_data_id = IntProperty(
        default=0
    )
    bpy.types.Scene.smc_list_id = IntProperty(
        default=0
    )

    bpy.types.Scene.smc_size = EnumProperty(
        name='Atlas Dimensions',
        items=_ATLAS_SIZE_ITEMS,
        default=_DEFAULT_ATLAS_SIZE,
        description='Texture atlas sizing strategy'
    )

    dimension_args = {
        'min': _MIN_DIMENSION,
        'max': _MAX_DIMENSION,
        'description': 'Maximum texture dimension in pixels'
    }
    bpy.types.Scene.smc_size_width = IntProperty(
        name='Width',
        default=_DEFAULT_DIMENSION,
        **dimension_args
    )
    bpy.types.Scene.smc_size_height = IntProperty(
        name='Height',
        default=_DEFAULT_DIMENSION,
        **dimension_args
    )

    bpy.types.Scene.smc_crop = BoolProperty(
        name='Crop UVs',
        default=True,
        description='Crop textures based on UV boundaries'
    )

    bpy.types.Scene.smc_pixel_art = BoolProperty(
        name='Pixel Art Mode',
        default=False,
        description='Optimize settings for pixel art textures'
    )

    bpy.types.Scene.smc_diffuse_size = IntProperty(
        name='Color Texture Size',
        min=8,
        max=256,
        default=32,
        description='Base size for color-only materials'
    )

    bpy.types.Scene.smc_gaps = IntProperty(
        name='Padding Size',
        min=0,
        max=32,
        default=0,
        options={'HIDDEN'},
        description='Spacing between atlas elements'
    )

    bpy.types.Scene.smc_save_path = StringProperty(
        name='Save Location',
        default='',
        subtype='DIR_PATH',
        description='Output directory for generated atlas'
    )


def _register_material_properties() -> None:
    bpy.types.Material.root_mat = PointerProperty(
        name='Base Material',
        type=bpy.types.Material,
        description='Original material reference'
    )

    bpy.types.Material.smc_diffuse = BoolProperty(
        name='Multiply Color',
        default=True,
        description='Blend diffuse color with texture'
    )

    bpy.types.Material.smc_size = BoolProperty(
        name='Custom Size',
        default=False,
        description='Enable custom texture dimensions'
    )

    dimension_args = {
        'min': _MIN_DIMENSION,
        'max': _MAX_DIMENSION // 2,
        'description': 'Maximum texture dimension in pixels'
    }
    bpy.types.Material.smc_size_width = IntProperty(
        name='Width',
        default=2048,
        **dimension_args
    )
    bpy.types.Material.smc_size_height = IntProperty(
        name='Height',
        default=2048,
        **dimension_args
    )


def register() -> None:
    _register_scene_properties()
    _register_material_properties()


def unregister() -> None:
    for prop in _SCENE_PROPS:
        if hasattr(bpy.types.Scene, prop):
            delattr(bpy.types.Scene, prop)

    for prop in _MATERIAL_PROPS:
        if hasattr(bpy.types.Material, prop):
            delattr(bpy.types.Material, prop)
