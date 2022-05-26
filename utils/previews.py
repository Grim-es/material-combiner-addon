import bpy

# Technically works with any Blender ID, not just materials and images
if bpy.app.version >= (3, 0):
    # Breaking Python API change in the 3.0 release notes:
    # "ID preview can be None, can use the new preview_ensure function first then."
    def get_preview(mat_or_image):
        preview = mat_or_image.preview
        if preview:
            return preview
        else:
            return mat_or_image.preview_ensure()
else:
    def get_preview(mat_or_image):
        return mat_or_image.preview
