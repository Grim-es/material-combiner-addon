import bgl

import numpy as np
import array

from .pixel_types import pixel_gltype, pixel_dtype, pixel_ctype

# These functions are the last resort ways to get and set pixels to/from numpy arrays that are still faster than most
# other simpler and safer methods, but are generally still quite slow.


# Faster than any other simple/naive approach I could find
# 200.3ms for 1024x1024
# 819.8ms for 2048x2048
# 3343.8 for 4096x4096
# 33066.2 for 8192x8192
def get_pixels_no_gl(image):
    return np.fromiter(image.pixels, dtype=pixel_dtype)


# This only works on 2.79 and older due to changes to image.bindcode and image.gl_load in newer Blender versions.
# Getting pixels through Open GL and then into a numpy array via np.fromiter(buffer, dtype=pixel_dtype).
#
# Blender 2.80 to 2.82 have a fast, safe method of getting image pixels, so this fallback is never needed in those
# versions.
#
# 159.6ms for 1024x1024
# 636.5ms for 2048x2048
# 2600.7ms for 4096x4096
# 10215.1ms for 8192x8192
def get_pixels_gl_buffer_iter_2_79(image):
    pixels = image.pixels
    if image.bindcode[0]:
        image.gl_free()
    if image.gl_load(0, bgl.GL_NEAREST, bgl.GL_NEAREST):
        print("Could not load {} into Open GL, resorting to a slower method of getting pixels".format(image))
        return get_pixels_no_gl(image)
    num_pixel_components = len(pixels)
    bgl.glEnable(bgl.GL_TEXTURE_2D)
    bgl.glActiveTexture(bgl.GL_TEXTURE0)
    bgl.glBindTexture(bgl.GL_TEXTURE_2D, image.bindcode[0])

    # Create a bgl.Buffer and fill it with the pixels of the image
    gl_buffer = bgl.Buffer(pixel_gltype, num_pixel_components)
    bgl.glGetTexImage(bgl.GL_TEXTURE_2D, 0, bgl.GL_RGBA, pixel_gltype, gl_buffer)

    # Return a numpy ndarray created from the bgl.Buffer
    return np.fromiter(gl_buffer, dtype=pixel_dtype)


# From https://devtalk.blender.org/t/bpy-data-images-perf-issues/6459 discussing the performance of Image.pixels,
# this was considered the fastest method (re-timed on my computer)
# 110.6ms for 1024x1024
# 487.5ms for 2048x2048
# 1991.8ms for 4096x4096 - uses about 3GB of memory
# 15483.5ms for 8192x8192 - maxes out my 16GB RAM, so the time is inaccurate; presumably uses about 12GB of memory
# img.pixels[:] = buffer.tolist()
#
# In most cases, it's faster to set the value of each element instead of replacing the entire pixels attribute,
# but that doesn't seem to be the case for Python arrays for some reason. My best guess as to why, is that while
# the entire array must be iterated as per normal, iterating Python arrays is fairly fast and there is little
# conversion required for each element as they are already single precision floats.
# This method also requires very little memory compared to the other options, making it significantly faster for larger
# images on lower RAM systems and possibly also on systems with slower RAM (but it could just be that freeing the memory
# as it goes)
# Doing img.pixels = buffer.ravel() has the same effect of lower memory overhead, but is much slower.
# 85.5ms for 1024x1024
# 388.2 for 2048x2048
# 1511.1ms for 4096x4096
# 6407.5ms for 8192x8192 - uses about 2GB of memory
def set_pixels_array_assign(img, buffer):
    # Converting to bytes (with default arguments) effectively converts to C contiguous and flattens.
    # buffer.tobytes() seems to be the fastest way to get an ndarray into a Python array
    img.pixels = array.array(pixel_ctype, buffer.tobytes())
