import bpy

is_blender_2_79_or_older = bpy.app.version < (2, 80, 0)
is_blender_2_80_or_newer = not is_blender_2_79_or_older
is_blender_2_81_or_newer = bpy.app.version >= (2, 81)

# Change to True to enable debug print statements
debug = True
if not debug:
    def debug_print(*_args, **_kwargs):
        pass
else:
    debug_print = print

smc_pi = False

# CombineList type constants
C_L_OBJECT = 0
C_L_MATERIAL = 1
