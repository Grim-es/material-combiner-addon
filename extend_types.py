import bpy
import bpy.utils.previews
from bpy.props import *
from . import addon_updater_ops

preview_collections = {}
preview = None
image_preview = None
images = []


def mats_preview(self, context):
    previews = []
    index = 0
    for mat in bpy.data.materials:
        if not mat.users: continue
        previews.append((mat.name, mat.name, '', mat.preview.icon_id, index))
        index += 1
    pcoll = preview_collections['smc_mats']
    pcoll.smc_mats_previews = previews
    return pcoll.smc_mats_previews


def images_preview(self, context):
    scn = context.scene
    image_previews = []
    index = 0
    for item in scn.smc_multi_list:
        image_previews.append((item.image.name, item.image.name, '', item.image.preview.icon_id, index))
        index += 1
    pcoll = preview_collections['smc_image']
    pcoll.smc_image_previews = image_previews
    return pcoll.smc_image_previews


class ObData(bpy.types.PropertyGroup):
    ob = PointerProperty(
        name='Current Object',
        type=bpy.types.Object)
    ob_id = IntProperty(default=0)
    mat = PointerProperty(
        name='Current Object Material',
        type=bpy.types.Material)
    layer = IntProperty(
        description='Choose id of material to which you want to combine',
        min=1,
        max=99,
        step=1,
        default=1)
    used = BoolProperty(default=True)
    data_type = IntProperty(default=0)


class ImagePreview(bpy.types.PropertyGroup):
    image = PointerProperty(
        name='Images to multicombine',
        type=bpy.types.Image)


class ImageItems(bpy.types.PropertyGroup):
    img_name = StringProperty(default='')
    img_path = StringProperty(default='')
    img_type = IntProperty(default=0)
    img_color = FloatVectorProperty(
        name='Hex Value',
        subtype='COLOR',
        size=3,
        min=0,
        max=1,
        precision=3,
        step=0.1,
        default=[1.0, 1.0, 1.0],
    )


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
    bpy.types.Scene.smc_mats_preview = EnumProperty(
        name='Selected object Materials',
        items=mats_preview)
    global preview
    preview = bpy.utils.previews.new()
    preview.smc_mats_preview = ()
    preview_collections['smc_mats'] = preview
    bpy.types.Scene.smc_image_preview = EnumProperty(
        name='Images to combine list',
        items=images_preview)
    global image_preview
    image_preview = bpy.utils.previews.new()
    image_preview.smc_image_preview = ()
    preview_collections['smc_image'] = image_preview

    bpy.types.Scene.smc_size = EnumProperty(
        name='Image size',
        items=(
            ('PO2', 'Power of 2', 'Combined image has same width and height'),
            ('AUTO', 'Automatic', 'Combined image has minimal size'),
            ('CUST', 'Custom', 'Use max width and height')),
        description='Select combined image size',
        default='PO2')
    bpy.types.Scene.smc_size_width = IntProperty(
        name='Max width',
        description='Select max width for combined image',
        min=8,
        max=8192,
        step=1,
        default=1024)
    bpy.types.Scene.smc_size_height = IntProperty(
        name='Max height',
        description='Select max height for combined image',
        min=8,
        max=8192,
        step=1,
        default=1024)
    bpy.types.Scene.smc_combine_state = EnumProperty(
        name='Combine menu state',
        items=(('MATS', 'Materials', 'Materials setup page'),
               ('COMB', 'Combine', 'Select items to combine page'),
               ('MULT', 'Multicombining', 'Multicombining page'))
    )
    bpy.types.Scene.smc_help_state = EnumProperty(
        name='Material Combiner by Shotariya#4269',
        items=(
            ('COMB', 'Combining', ''),
            ('SIZE', 'Sizing', ''),
            ('TRANS', 'Transparent', ''),
            ('TEX', 'UVTextures', ''),
            ('SPLIT', 'UVSplitting', ''),
            ('COMP', 'Compression', '')),
        description='Choose what info you are looking for',
        default='COMB')
    bpy.types.Scene.smc_ob_data = CollectionProperty(type=ObData)
    bpy.types.Scene.smc_ob_data_id = IntProperty(default=0)
    bpy.types.Scene.smc_save_path = StringProperty(
        description='Select a path for combined texture',
        default='')
    bpy.types.Scene.smc_compress = BoolProperty(default=True)
    bpy.types.Scene.smc_multi = BoolProperty(
        name='Multicombining',
        description='Select to combine all material texture layers',
        default=False)
    bpy.types.Scene.smc_multi_list = CollectionProperty(type=ImagePreview)

    bpy.types.Material.smc_size = BoolProperty(
        name='Use custom material size',
        description='Select to have same side sized combined image',
        default=False)
    bpy.types.Material.smc_size_width = IntProperty(
        name='Max width',
        description='Select max width for combined image',
        min=8,
        max=8192,
        step=1,
        default=1024)
    bpy.types.Material.smc_size_height = IntProperty(
        name='Max height',
        description='Select max height for combined image',
        min=8,
        max=8192,
        step=1,
        default=1024)
    bpy.types.Material.smc_diffuse = BoolProperty(
        name='Apply material diffuse',
        description='Multiply material color with material image',
        default=True)

    bpy.types.Image.smc_img_list = CollectionProperty(type=ImageItems)
    bpy.types.Image.smc_img_list_id = IntProperty(default=0)


def unregister():
    bpy.utils.previews.remove(preview)
    bpy.utils.previews.remove(image_preview)

    del bpy.types.Scene.smc_mats_preview
    del bpy.types.Scene.smc_image_preview
    del bpy.types.Scene.smc_size
    del bpy.types.Scene.smc_size_width
    del bpy.types.Scene.smc_size_height
    del bpy.types.Scene.smc_help_state
    del bpy.types.Scene.smc_ob_data
    del bpy.types.Scene.smc_ob_data_id
    del bpy.types.Scene.smc_save_path
    del bpy.types.Scene.smc_compress
    del bpy.types.Scene.smc_multi

    del bpy.types.Material.smc_size
    del bpy.types.Material.smc_size_width
    del bpy.types.Material.smc_size_height
    del bpy.types.Material.smc_diffuse

    del bpy.types.Image.smc_img_list
    del bpy.types.Image.smc_img_list_id
