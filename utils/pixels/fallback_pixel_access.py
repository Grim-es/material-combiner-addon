import bgl

import numpy as np
import array

from .pixel_types import pixel_gltype, pixel_dtype

# These functions are the last resort ways to get and set pixels to/from numpy arrays that are still faster than most
# other simpler and safer methods, but are generally still quite slow.


# Faster than any other simple/naive approach I could find, but is memory hungry, uses about 2GB memory while reading a
# 4k image
# 149.9ms for 1024x1024
# 592.4ms for 2048x2048
# 2437.9ms for 4096x4096
# 10656.4ms for 8192x8192, uses about 8GB of memory while reading
def get_pixels_no_gl(image):
    return np.array(image.pixels[:], dtype=pixel_dtype)


# This only works on 2.79 and older due to changes to image.bindcode in newer Blender versions.
# Getting pixels through Open GL and then into a numpy array via np.fromiter(buffer, dtype=pixel_dtype).
#
# Blender 2.80 to 2.82 have a fast, safe method of getting image pixels, so this fallback is never needed in those
# versions.
#
# 161.0ms for 1024x1024
# 630.3ms for 2048x2048
# 2544.3ms for 4096x4096
# 10110.2ms for 8192x8192, uses about 2GB of memory while reading
def get_pixels_gl_buffer_iter_2_79(image):
    if image.is_float:
        # gl_load fails with an error on 2.79 when the image uses a float buffer internally, this seems to be a bug in
        # Blender
        return get_pixels_no_gl(image)
    pixels = image.pixels
    if image.bindcode[0]:
        image.gl_free()
    if image.gl_load():
        print("Could not load {} into Open GL, resorting to a slower method of getting pixels".format(image))
        return get_pixels_no_gl(image)
    num_pixel_components = len(pixels)
    bgl.glActiveTexture(bgl.GL_TEXTURE0)
    bgl.glBindTexture(bgl.GL_TEXTURE_2D, image.bindcode[0])

    # Create a bgl.Buffer and fill it with the pixels of the image
    gl_buffer = bgl.Buffer(pixel_gltype, num_pixel_components)
    bgl.glGetTexImage(bgl.GL_TEXTURE_2D, 0, bgl.GL_RGBA, pixel_gltype, gl_buffer)

    # Return a numpy ndarray created from the bgl.Buffer
    return np.fromiter(gl_buffer, dtype=pixel_dtype)


# From https://devtalk.blender.org/t/bpy-data-images-perf-issues/6459 discussing the performance of Image.pixels,
# this was considered the fastest method (re-timed on my computer)
# 100.9ms for 1024x1024
# 410.9ms for 2048x2048
# 1656.4ms for 4096x4096
# 6868.7ms for 8192x8192 - uses about 8GB of memory
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
# 92.0ms for 1024x1024
# 373.5 for 2048x2048
# 1498.8ms for 4096x4096
# 6168.8ms for 8192x8192 - uses about 2GB of memory
def set_pixels_array_assign(img, buffer):
    # Ensure the pixels array is flat (1 dimensional) and is C-contiguous in memory
    buffer = buffer.ravel()
    # Create a Python array of the correct size
    p_array = array.array(np.sctype2char(buffer.dtype), [0])
    # Create a numpy array that shares the same memory as the Python array
    p_array_as_np = np.frombuffer(p_array, dtype=np.single)
    # Directly copy the values into the Python array by using the numpy array that shares the same memory
    # Technically, we could avoid this and the previous step if we'd used a Python array to start with, but then
    # we'd have to juggle around both a Python array and
    p_array_as_np[:] = buffer
    # Set image.pixels to the array, which seems to be the fastest way to update pixels (Python arrays are fast to
    # iterate and there should be minimal, if any, type conversion needed in the Blender C code)
    img.pixels = p_array
