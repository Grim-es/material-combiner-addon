import numpy as np
import bgl


# The C type code for single precision float, for use with Python arrays
pixel_ctype = 'f'

# Image.pixels is a bpy_prop_array, to use its foreach_get/foreach_set methods with buffers, the buffer's type has to
# match the internal C type used by Blender, otherwise Blender will reject the buffer.
#
# Note that this is different to the behaviour of the foreach_get and foreach_set methods on bpy_prop_collection objects
# which allow for the type to be different by casting every value to the new type (which you generally want to avoid
# anyway because it slows things down)
# Single precision float dtype for use with numpy functions
pixel_dtype = np.single

# The Open GL type used for reading pixels.
# A bgl.GL_BYTE bgl.Buffer alongside bgl.GL_UNSIGNED_BYTE bgl.glGetTexImage might be faster, but it can only be used for
# images with 8-bits per channel.
# Any Image in blender using a float buffer internally has to use bgl.GL_FLOAT, otherwise there will be a loss of
# precision.
# For simplicity, bgl.GL_FLOAT is being used for all images.
pixel_gltype = bgl.GL_FLOAT
