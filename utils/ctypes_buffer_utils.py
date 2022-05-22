import bpy
if bpy.app.version >= (2, 80):
    raise RuntimeError("ctypes buffer utils was attempted to be loaded on Blender version >=2.80")

import bgl
import numpy as np
import ctypes
from .ctypes_utils import PyVarObject
# This module is only used for Blender 2.79 and older where there is no fast method to get all of an Image's pixels into
# a numpy array
# When importing this module, make sure to surround it in a try block and have some sort of backup plan if it fails


# Declare class to mirror bgl.Buffer's _Buffer type
# The fields for bgl.Buffer haven't been changed since its introduction, but if they are changed in the future, then
# this class would need to be modified to match. Fortunately, we only need to use this when in Blender 2.79 and earlier,
# so it's not going to change.
class BglBuffer(PyVarObject):
    """https://github.com/blender/blender/blob/master/source/blender/python/generic/bgl.h
    For the PyObject_VAR_HEAD macro, see https://docs.python.org/3/c-api/structures.html#c.PyObject_VAR_HEAD
    /**
     * Buffer Object
     *
     * For Python access to OpenGL functions requiring a pointer.
     */
    typedef struct _Buffer {
      PyObject_VAR_HEAD
      PyObject *parent;

      int type; /* GL_BYTE, GL_SHORT, GL_INT, GL_FLOAT */
      int ndimensions;
      int *dimensions;

      union {
        char *asbyte;
        short *asshort;
        int *asint;
        float *asfloat;
        double *asdouble;

        void *asvoid;
      } buf;
    } Buffer;"""
    _fields_ = [
        ('parent', ctypes.py_object),
        ('type', ctypes.c_int),
        ('ndimensions', ctypes.c_int),
        ('dimensions', ctypes.POINTER(ctypes.c_int)),
        ('buf', ctypes.c_void_p),
    ]


# Ensure the size matches what Python tells us
assert bgl.Buffer.__basicsize__ == ctypes.sizeof(BglBuffer)


def gl_get_tex_image_to_numpy(num_pixel_components, pixel_gltype, pixel_dtype):
    # Create as minimal a bgl.Buffer as possible
    gl_buffer = bgl.Buffer(pixel_gltype, 1)  # Minimum accepted dimension is 1
    # Get the corresponding ctypes object
    c_buffer = BglBuffer.from_address(id(gl_buffer))
    # Create the np ndarray
    np_array = np.empty(num_pixel_components, dtype=pixel_dtype)

    # Store the old fields that we're going to change
    old_ndimensions = c_buffer.ndimensions
    # It seems to work even if we don't change the 0th dimension size, but it's probably a good idea to set it correctly
    old_dimensions0 = c_buffer.dimensions[0]
    # c_void_p is directly accessed as a memory address
    old_buf_address = c_buffer.buf

    try:
        # Set the fields to those used by the ndarray
        # ndimensions should already be 1, so this shouldn't change anything
        c_buffer.ndimensions = 1  # numpy array is flat, so only 1 dimension
        # 0th dimension length is the entire length of the numpy array
        c_buffer.dimensions[0] = num_pixel_components
        c_buffer.buf = np_array.ctypes.data

        # Copy pixels into the gl_buffer, which we've set up to share the same memory as the ndarray, meaning that the
        # pixels get put into the ndarray
        bgl.glGetTexImage(bgl.GL_TEXTURE_2D, 0, bgl.GL_RGBA, pixel_gltype, gl_buffer)
    finally:
        # ALWAYS set the fields back to the old values to avoid memory leaks/corruption
        c_buffer.buf = old_buf_address
        c_buffer.dimensions[0] = old_dimensions0
        c_buffer.ndimensions = old_ndimensions

    # The image pixels are now in the ndarray
    return np_array
