import bpy

try:
    from PIL import Image
    from PIL import ImageChops

    pil_exist = True
except ImportError:
    pil_exist = False

version = bpy.app.version >= (2, 80, 0)
smc_pi = False
