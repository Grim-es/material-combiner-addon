import bpy

# TODO: Replace 'version' with human readable constant values
# # Old value: 0/Falsey
# is_blender_2_79_or_older = bpy.app.version < (2, 80, 0)
# # Old value: 1
# is_blender_2_80 = not is_blender_2_79_or_older and bpy.app.version < (2, 81)
# # Old value: >0/Truthy
# is_blender_2_80_or_newer = not is_blender_2_79_or_older
# # Old value: 2
# is_blender_2_81_or_newer = bpy.app.version >= (2, 81)

version = 0 if bpy.app.version < (2, 80, 0) else 2 if bpy.app.version > (2, 80, 99) else 1
smc_pi = False

# TODO: Replace the 'type' IntProperty in extend_types.CombineList with an EnumProperty with options: ['OBJECT', 'MATERIAL', 'END']
# CombineList type constants
C_L_OBJECT = 0
C_L_MATERIAL = 1
C_L_END = 2
