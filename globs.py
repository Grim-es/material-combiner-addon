import bpy

version = 0 if bpy.app.version < (2, 80, 0) else 2 if bpy.app.version > (2, 80, 99) else 1
smc_pi = False
