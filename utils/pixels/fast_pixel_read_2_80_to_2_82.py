import numpy as np

import bgl

from .pixel_types import pixel_gltype, pixel_dtype
from .fallback_pixel_access import get_pixels_no_gl

# 2.80 added the ability to create bgl.Buffer objects that share the same memory as an object that implements the Python
# buffer protocol


# see https://blender.stackexchange.com/a/230242 for details
def get_pixels_gl_shared_buffer(image):
    pixels = image.pixels
    # Load the image into OpenGL and use that to get the pixels in a more performant manner
    # As per the documentation, the colours will be read in scene linear color space and have premultiplied or
    # straight alpha matching the image alpha mode.
    # Open GL will cache the image if we've used it previously, this means that if we update the image in Blender
    # it won't have updated in Open GL unless we free it first. There isn't really a way to know if the image has
    # changed since it was last cached, so we'll always free it first.
    if image.bindcode:
        # If the open gl bindcode is set, then it's already been cached, so free it from open gl first
        image.gl_free()
    if image.gl_load():
        print("Could not load {} into Open GL, resorting to a slower method of getting pixels".format(image))
        return get_pixels_no_gl(image)
    bgl.glActiveTexture(bgl.GL_TEXTURE0)
    bgl.glBindTexture(bgl.GL_TEXTURE_2D, image.bindcode)
    buffer = np.empty(len(pixels), dtype=pixel_dtype)
    # Create a bgl.Buffer that shares the same memory as the numpy array
    gl_buffer = bgl.Buffer(pixel_gltype, buffer.shape, buffer)
    bgl.glGetTexImage(bgl.GL_TEXTURE_2D, 0, bgl.GL_RGBA, pixel_gltype, gl_buffer)
    return buffer
