import bpy
import sys
import site

sys.path.insert(0, site.getusersitepackages())

try:
    from PIL import Image
    from PIL import ImageChops

    pil_exist = True
except ImportError:
    pil_exist = False

version = 0 if bpy.app.version < (2, 80, 0) else 2 if bpy.app.version > (2, 80, 99) else 1
smc_pi = False
