import bpy
from bpy.props import *
from . import addon_updater_ops


class CombineList(bpy.types.PropertyGroup):
    ob = PointerProperty(
        name='Current Object',
        type=bpy.types.Object)
    ob_id = IntProperty(default=0)
    mat = PointerProperty(
        name='Current Object Material',
        type=bpy.types.Material)
    layer = IntProperty(
        description='Materials with the same number will be merged together.'
                    '\nUse this to create multiple materials linked to the same atlas file',
        min=1,
        max=99,
        step=1,
        default=1)
    used = BoolProperty(default=True)
    type = IntProperty(default=0)


class UpdatePreferences(bpy.types.AddonPreferences):
    bl_idname = __package__
    auto_check_update = BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=True,
    )
    updater_intrval_months = bpy.props.IntProperty(
        name='Months',
        description="Number of months between checking for updates",
        default=0,
        min=0
    )
    updater_intrval_days = IntProperty(
        name='Days',
        description="Number of days between checking for updates",
        default=1,
        min=1
    )
    updater_intrval_hours = IntProperty(
        name='Hours',
        description="Number of hours between checking for updates",
        default=0,
        min=0,
        max=0
    )
    updater_intrval_minutes = IntProperty(
        name='Minutes',
        description="Number of minutes between checking for updates",
        default=0,
        min=0,
        max=0
    )

    def draw(self, context):
        addon_updater_ops.update_settings_ui(self, context)


def register():
    bpy.types.Scene.smc_ob_data = CollectionProperty(type=CombineList)
    bpy.types.Scene.smc_ob_data_id = IntProperty(default=0)
    bpy.types.Scene.smc_list_id = IntProperty(default=0)
    bpy.types.Scene.smc_size = EnumProperty(
        name='Atlas size',
        items=(
            ('PO2', 'Power of 2', 'Combined image size is power of 2'),
            ('QUAD', 'Quadratic', 'Combined image has same width and height'),
            ('AUTO', 'Automatic', 'Combined image has minimal size'),
            ('CUST', 'Custom', 'Custom max width and height')),
        description='Select atlas size',
        default='QUAD')
    bpy.types.Scene.smc_size_width = IntProperty(
        name='Max width (px)',
        description='Select max width for combined image',
        min=8,
        max=8192,
        step=1,
        default=8192)
    bpy.types.Scene.smc_size_height = IntProperty(
        name='Max height (px)',
        description='Select max height for combined image',
        min=8,
        max=8192,
        step=1,
        default=8192)
    bpy.types.Scene.smc_crop = BoolProperty(
        name='Crop images by UV (Alpha)',
        description="This cuts away unused space from images",
        default=False
    )
    bpy.types.Scene.smc_diffuse_size = IntProperty(
        name='Size of materials without image',
        description='Select the size of materials that only consist of a color',
        min=8,
        max=256,
        step=1,
        default=32)
    bpy.types.Scene.smc_gaps = FloatProperty(
        name='Size of gaps between images',
        description='Select size of gaps between images',
        min=0,
        max=32,
        precision=0,
        step=200,
        default=2,
        options={'HIDDEN'})
    bpy.types.Scene.smc_save_path = StringProperty(
        description='Select the directory in which the generated texture atlas will be saved',
        default='')

    bpy.types.Material.root_mat = PointerProperty(
        name='Material Root',
        type=bpy.types.Material)
    bpy.types.Material.smc_diffuse = BoolProperty(
        name='Multiply image with diffuse color',
        description='Multiply the materials image with its diffuse color.'
                    '\nINFO: If this color is white the final image will be the same',
        default=True)
    bpy.types.Material.smc_size = BoolProperty(
        name='Custom image size',
        description='Select the max size for this materials image in the texture atlas',
        default=False)
    bpy.types.Material.smc_size_width = IntProperty(
        name='Max width (px)',
        description='Select max width for material image',
        min=8,
        max=8192,
        step=1,
        default=2048)
    bpy.types.Material.smc_size_height = IntProperty(
        name='Max height (px)',
        description='Select max height for material image',
        min=8,
        max=8192,
        step=1,
        default=2048)


def unregister():
    del bpy.types.Scene.smc_ob_data
    del bpy.types.Scene.smc_ob_data_id
    del bpy.types.Scene.smc_list_id
    del bpy.types.Scene.smc_size
    del bpy.types.Scene.smc_size_width
    del bpy.types.Scene.smc_size_height

    del bpy.types.Material.root_mat
    del bpy.types.Material.smc_diffuse
    del bpy.types.Material.smc_size
    del bpy.types.Material.smc_size_width
    del bpy.types.Material.smc_size_height
