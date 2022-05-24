# Used by Blender versions < (2, 83) to save atlases as images almost as fast as foreach_set.
# It does this by hacking into a Matrix object to set its data pointer to point to the pixel_buffer's data and hacking
# the number of columns and rows way above the usual limit of 4x4 so that the total size matches the number of pixel
# components.
# It then hacks into the image's .pixels property to temporarily set its number of dimensions to 2 and the size of both
# dimensions to match the hacked Matrix.
# Then, setting image.pixels = hacked_matrix performs a direct memcpy of all the Matrix's data to the image.pixels'
# data.
# Once done, all the hacked values are restored to avoid memory leaks/corruption and the Matrix is deleted.

import bpy
from bpy.app import version as blender_version

if blender_version >= (2, 83):
    # 2.83 and newer have Image.pixels.foreach_set so this module isn't needed (and no code has been specifically tested
    # on 2.83 or higher, though it does appear to work on 2.93 where it was benchmarked against foreach_set)
    raise RuntimeError("ctypes fast pixel write was attempted to be loaded on Blender version 2.83 or newer where it is"
                       " not needed")

# The oldest version that can possibly be supported is 2.63, when the direct memory copy feature when using a Matrix
# was added
# The oldest PropertyRNA we're currently supporting is 2.63
# The oldest PropertyArrayRNA we're currently supporting is 2.56
# The oldest PropArrayLengthGetFunc we're supporting is 2.50 (when PropArrayLengthGetFunc was added to Blender)
# The oldest PointerRNA we're supporting is 2.50 (when PointerRNA was added to Blender)
# These combined give the oldest supported version as 2.63, though testing has only been done on as old as 2.79
if blender_version < (2, 79):
    if blender_version < (2, 63):
        raise RuntimeError("ctypes fast pixel write does not support Blender versions older than 2.63")
    else:
        print("WARNING: Material Combiner's ctypes fast pixel write is untested on Blender versions older than 2.79,"
              " but might work on as old as 2.63")

import ctypes
import numpy as np

from mathutils import Matrix

from .ctypes_base import PyVarObject, PyObject

# This magic value is an internal Blender hack used to determine if a PropertyRNA is not an IDProperty
# Defined in source/blender/makesrna/intern/rna_internal.h
"""#define RNA_MAGIC ((int)~0)"""
RNA_MAGIC = -1


# Defined in source/blender/makesrna/RNA_types.h
# As a note, StructRNA is defined in source/blender/makesrna/intern/rna_internal_types.h
# This class must be fully mirrored as it is the type of a field in PropertyArrayRNA
class PointerRNA(ctypes.Structure):
    # Fields defined below because they were changed in Blender 2.81 and the older fields contain an extra struct that
    # needs to be defined
    pass


# I don't think it actually matters which fields are used, because the size of the fields will be the same and this code
# doesn't use the field that changed in Blender 2.81.
if blender_version < (2, 81):
    # 2.50.x to 2.80.x
    # Defined inside PointerRNA in source/blender/makesrna/RNA_types.h
    class PointerRNAID(ctypes.Structure):
        """
        struct {
            void *data;
        } id;
        """
        _fields_ = [
            ('data', ctypes.c_void_p),
        ]

    """
    typedef struct PointerRNA {
        struct {
            void *data;
        } id;

        struct StructRNA *type;
        void *data;
    } PointerRNA;
    """
    PointerRNA._fields_ = [
        ('id', PointerRNAID),
        ('type', ctypes.c_void_p),  # We don't need the StructRNA type for anything, so we'll leave it as c_void_p
        ('data', ctypes.c_void_p),
    ]

else:
    # 2.81.x to 2.82.x
    """
    typedef struct PointerRNA {
      struct ID *owner_id;
      struct StructRNA *type;
      void *data;
    } PointerRNA;
    """
    PointerRNA._fields_ = [
        ('owner_id', ctypes.c_void_p),  # We don't need the ID type for anything, so we'll leave it as c_void_p
        ('type', ctypes.c_void_p),  # We don't need the StructRNA type for anything, so we'll leave it as c_void_p
        ('data', ctypes.c_void_p),
    ]

# defined in source/blender/makesrna/intern/rna_internal_types.h
# RNA_MAX_ARRAY_DIMENSION = 3

# defined in source/blender/makesrna/intern/rna_internal_types.h
# No changes have been made between Blender 2.50 and 2.82
"""typedef int (*PropArrayLengthGetFunc)(struct PointerRNA *ptr, int length[RNA_MAX_ARRAY_DIMENSION]);"""
# ctypes.POINTER(ctypes.c_int) is technically the wrong second argument type, it should be
# (ctypes.c_int * RNA_MAX_ARRAY_DIMENSION), an int[RNA_MAX_ARRAY_DIMENSION], but this doesn't seem to work, presumably
# because arrays aren't actually passed by value. It works with an int pointer instead.
PropArrayLengthGetFunc = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(PointerRNA), ctypes.POINTER(ctypes.c_int))


# Defined in source/blender/makesrna/intern/rna_internal_types.h
# There have been no changes to PropertyRNA between 2.80 and 2.82 (only considering down to the arraydimension field)
# PropertyRNA changed in 2.80 from last being changed in 2.79. (only considering down to the arraydimension field)
# PropertyRNA changed in 2.79 from last being changed in 2.63. (only considering down to the arraydimension field)
# As no fields have been removed or reordered, only the PropertyRNA as seen in 2.82 is shown, as the older versions
# can be inferred from the change in fields
class PropertyRNA(ctypes.Structure):
    """
    struct PropertyRNA {
      struct PropertyRNA *next, *prev;

      /* magic bytes to distinguish with IDProperty */
      int magic;

      /* unique identifier */
      const char *identifier;
      /* various options */
      int flag;
      /* various override options */
      int flag_override;                                [Added in 2.80]
      /* Function parameters flags. */
      short flag_parameter;                             [Added in 2.79]
      /* Internal ("private") flags. */
      short flag_internal;                              [Added in 2.79]
      /* The subset of StructRNA.prop_tag_defines values that applies to this property. */
      short tags;                                       [Added in 2.80]

      /* user readable name */
      const char *name;
      /* single line description, displayed in the tooltip for example */
      const char *description;
      /* icon ID */
      int icon;
      /* context for translation */
      const char *translation_context;

      /* property type as it appears to the outside */
      PropertyType type;
      /* subtype, 'interpretation' of the property */
      PropertySubType subtype;
      /* if non-NULL, overrides arraylength. Must not return 0? */
      PropArrayLengthGetFunc getlength;
      /* dimension of array */
      unsigned int arraydimension;
      [...remaining fields omitted]
    };
    """
    # Fields must be declared after the class declaration because the fields contain pointers to own type
    # (technically, since we're not using the 'next' and 'prev' fields we could set their type to c_void_p instead)
    pass


# Common for each version
_property_rna_fields_start = [
    ('next', ctypes.POINTER(PropertyRNA)),
    ('prev', ctypes.POINTER(PropertyRNA)),
    ('magic', ctypes.c_int),
    ('identifier', ctypes.c_char_p),
    ('flag', ctypes.c_int)
]
_property_rna_fields_end = [
    ('name', ctypes.c_char_p),
    ('description', ctypes.c_char_p),
    ('icon', ctypes.c_int),
    ('translation_context', ctypes.c_char_p),
    ('type', ctypes.c_uint),  # enum PropertyType
    ('subtype', ctypes.c_uint),  # enum PropertySubType
    ('getlength', PropArrayLengthGetFunc),
    ('arraydimension', ctypes.c_uint),
    # [...]
    # We only need up to arraydimension as we don't need any later fields, and we don't need any type that has a
    # PropertyRNA directly as a field (which would require knowing the full size of PropertyRNA).
]

if blender_version < (2, 79):
    # 2.63.x to 2.78.x
    _property_rna_fields_middle = []
elif blender_version < (2, 80):
    # 2.79.x
    _property_rna_fields_middle = [
        ('flag_parameter', ctypes.c_short),
        ('flag_internal', ctypes.c_short),
    ]
else:  # blender_Version < (2, 83)
    # 2.80.x to 2.82.x
    _property_rna_fields_middle = [
        ('flag_override', ctypes.c_int),
        ('flag_parameter', ctypes.c_short),
        ('flag_internal', ctypes.c_short),
        ('tags', ctypes.c_short),
    ]

# Assign the fields to a concatenation of all three lists
PropertyRNA._fields_ = _property_rna_fields_start + _property_rna_fields_middle + _property_rna_fields_end
# The original lists aren't needed any more and would otherwise remain available as part of this module, so delete them
del _property_rna_fields_start, _property_rna_fields_middle, _property_rna_fields_end


# defined in source/blender/python/intern/bpy_rna.h
# No changes made between Blender 2.56 and 2.82
class PropertyArrayRNA(PyObject):
    """
    typedef struct {
      PyObject_HEAD /* required python macro   */
    #ifdef USE_WEAKREFS
          PyObject *in_weakreflist;
    #endif
      PointerRNA ptr;
      PropertyRNA *prop;

      /* Arystan: this is a hack to allow sub-item r/w access like: face.uv[n][m] */
      /** Array dimension, e.g: 0 for face.uv, 2 for face.uv[n][m], etc. */
      int arraydim;
      /** Array first item offset, e.g. if face.uv is [4][2], arrayoffset for face.uv[n] is 2n. */
      int arrayoffset;
    } BPy_PropertyArrayRNA;
    """
    # Assuming USE_WEAKREFS is not defined
    _fields_ = [
        ('ptr', PointerRNA),
        ('prop', ctypes.POINTER(PropertyRNA)),
        ('arraydim', ctypes.c_int),
        ('arrayoffset', ctypes.c_int),
    ]


if bpy.types.bpy_prop_array.__basicsize__ != ctypes.sizeof(PropertyArrayRNA):
    class PropertyArrayRNA(PyObject):
        # Assuming USE_WEAKREFS is defined
        _fields_ = [
            ('in_weakreflist', ctypes.py_object),
            ('ptr', PointerRNA),
            ('prop', ctypes.POINTER(PropertyRNA)),
            ('arraydim', ctypes.c_int),
            ('arrayoffset', ctypes.c_int),
        ]

assert bpy.types.bpy_prop_array.__basicsize__ == ctypes.sizeof(PropertyArrayRNA)


# In source/blender/python/mathutils/mathutils.h and source/blender/python/mathutils/mathutils_Matrix.h
# No changes have been made between Blender 2.63 and 3.1.0 besides renaming the 'wrapped' field to what is now the
# 'flag' field, in 2.74
class MatrixObject(PyVarObject):
    """
    #define BASE_MATH_MEMBERS(_data) \
      /** Array of data (alias), wrapped status depends on wrapped status. */ \
      PyObject_VAR_HEAD float *_data; \
      /** If this vector references another object, otherwise NULL, *Note* this owns its reference */ \
      PyObject *cb_user; \
      /** Which user funcs do we adhere to, RNA, etc */ \
      unsigned char cb_type; \
      /** Subtype: location, rotation... \
       * to avoid defining many new functions for every attribute of the same type */ \
      unsigned char cb_subtype; \
      /** Wrapped data type. */ \
      unsigned char flag


    typedef struct {
      BASE_MATH_MEMBERS(matrix);
      ushort num_col;
      ushort num_row;
    } MatrixObject;
    """
    _fields_ = [
        ('matrix', ctypes.POINTER(ctypes.c_float)),
        ('cb_user', ctypes.py_object),
        ('cb_type', ctypes.c_ubyte),
        ('cb_subtype', ctypes.c_ubyte),
        ('flag', ctypes.c_ubyte),  # Called 'wrapped' before 2.74
        ('num_col', ctypes.c_ushort),
        ('num_row', ctypes.c_ushort),
    ]


# Compare against Matrix class to check
assert Matrix.__basicsize__ == ctypes.sizeof(MatrixObject)

# The number of Matrix rows and columns are stored as ushort, so the maximum number of pixel components we can pretend
# are in a Matrix is 65535 * 65535
# ushort_max = np.iinfo(np.ushort).max
# ushort_max = 2 ** (ctypes.sizeof(ctypes.c_ushort) * 8)
ushort_max = 65535


# Something I discovered looking through the Blender source code is that there is special code for handling assigning
# a Matrix to a bpy_prop_array of the FloatProperty type. If the number of dimensions of the bpy_prop_array and the size
# of each of those dimensions match the Matrix, the float values in the matrix are directly copied via memcpy.
#
# This is unlike assigning a list or other iterable to a bpy_prop_array which has to be iterated through, possibly
# converting every value from the iterable, which is much slower.
#
# 1.
# The first problem is that there is a hardcoded check that the bpy_prop_array has 2 dimensions. Image.pixels is a one
# dimensional array, so this is a problem. This can be worked around easy enough, as there is an arraydimension field in
# bpy_prop_array->prop that specifies the number of dimensions. We can temporarily set this value to 2.
#
# 2.
# The second problem is that there is a hardcoded check that the size of each dimension of the bpy_prop_array matches
# the size of each dimension of the Matrix. As Image.pixels has a dynamic size, its length and dimension sizes are
# retrieved via bpy_prop_array->prop.getlength.
#
# getlength is a function that returns the total length of the property, but it also has an int[RNA_MAX_ARRAY_DIMENSION]
# array parameter. When the getlength function is called, it sets the size of each dimension into its int array argument
# so that the code that called the function can find out the sizes of each dimension.
#
# The getlength function for Image.pixels sets the first index of the array to the total length of the Image.pixels
# because it only has one dimension, and leaves the remaining indices unchanged (usually uninitialised, so random values
# from memory).
#
# What we can do is swap out the getlength function with our own function that sets the values at the first and second
# array indices to the dimensions of the Matrix (and returns the same total length as before).
#
# 3.
# The next problem is that Matrix classes can only be created up to 4x4 (dimension 0 of length 4 and dimension 1 of
# length 4). Fortunately, this is easy to change by hacking the num_col and num_row fields of a Matrix to higher
# values through ctypes.
#
# 4.
# The final step is to set the Matrix's pointer to its data to instead point to the data in the pixel_buffer, which
# numpy makes easily available. With this and all the previous steps done, we can do "image.pixels = hacked_matrix"
# and Blender will directly copy the data from the pixel_buffer into image.pixels.
#
# 5.
# Once all done, it's extremely important to set every field that got changed on both the pixels bpy_prop_array and the
# temporarily created Matrix back to their original values otherwise Blender is likely to crash and/or leak memory.
#
# The main function that gets called when setting image.pixels = hacked_matrix is py_to_array:
#   https://github.com/blender/blender/blob/v2.82/source/blender/python/intern/bpy_rna_array.c#L529
# It first calls validate_array:
#   https://github.com/blender/blender/blob/v2.82/source/blender/python/intern/bpy_rna_array.c#L546
#   \-> gets the length and dimension sizes of image.pixels:
#       https://github.com/blender/blender/blob/v2.82/source/blender/python/intern/bpy_rna_array.c#L364
#       \-> https://github.com/blender/blender/blob/v2.82/source/blender/makesrna/intern/rna_access.c#L1209
#           \-> Where it then calls the getlength function if prop->magic == RNA_MAGIC and prop->getlength isn't NULL:
#               https://github.com/blender/blender/blob/v2.82/source/blender/makesrna/intern/rna_access.c#L465
#
#   Then it checks the dimensions of image.pixels:
#       https://github.com/blender/blender/blob/v2.82/source/blender/python/intern/bpy_rna_array.c#L385
#   And checks that the length of the dimensions of the array match the matrix here:
#       https://github.com/blender/blender/blob/v2.82/source/blender/python/intern/bpy_rna_array.c#L394
# If validate_array succeeds, it calls copy_values:
#   https://github.com/blender/blender/blob/v2.82/source/blender/python/intern/bpy_rna_array.c#L572
#   \-> https://github.com/blender/blender/blob/v2.82/source/blender/python/intern/bpy_rna_array.c#L460
#   Which copies the data from the matrix with memcpy:
#       https://github.com/blender/blender/blob/v2.82/source/blender/python/intern/bpy_rna_array.c#L495
#
# This process does not appear to have been changed since Blender 2.63, when the direct memcpy was added, to the current
# Blender 3.1.0. (though it's irrelevant in 2.83 and newer due to the introduction of image.pixels.foreach_set)
def set_pixels_matrix_hack(image, pixel_buffer):
    height, width, channels = pixel_buffer.shape
    if channels != 4:
        # Limitation is in place because we're assuming 4 in the matrix_rows and matrix_columns calculation
        raise TypeError("Only pixel_buffers with 4 channels supported")
    if channels != image.channels:
        raise TypeError("Image channels {} doesn't match pixel_buffer channels {}".format(image.channels, channels))
    if image.size[0] != width:
        raise TypeError("Image width {} doesn't match pixel_buffer width {}".format(image.size[0], width))
    if image.size[1] != height:
        raise TypeError("Image height {} doesn't match pixel_buffer height {}".format(image.size[1], height))

    # Matrix is only 2D, so we have to represent height * width * channels with only two numbers multiplied together.
    # Since the number of channels is 4, it's simple to split into 2 and 2
    matrix_rows = height * 2
    matrix_columns = width * 2

    # Total components must equal len(image.pixels) as this is the number of floats that will be copied from the
    # pixel_buffer to image.pixels. Less than len(image.pixels) is ok if only part of the pixel_buffer was to be copied,
    # but more than len(image.pixels) would be very bad since it can overwrite memory used by other things.
    total_components = matrix_rows * matrix_columns

    # Matrix columns and rows are limited to a maximum of 65535 due to being unsigned short type, this limits the
    # maximum image height and width to 32767 when the 4 channels are split 2 and 2 between the height and width.
    # 32767 pixels in one dimension is a huge image, which is unlikely to ever be needed, however, if support for larger
    # images is needed, we could set up the matrix to copy as much of the data as possible and then offset the matrix's
    # data pointer ('matrix') to one element after the copied data and copy another chunk of the data, repeatedly
    # copying more chunks until all the data has been copied.
    if matrix_rows > ushort_max or matrix_columns > ushort_max:
        raise TypeError("Image/Pixel buffer is too large, maximum width or height is {}".format(ushort_max // 2))

    # The pixel buffer must be C contiguous, otherwise when the memory is copied, the pixels will end up in the wrong
    # order.
    # If pixel_buffer was already C contiguous, this does nothing and simply returns pixel_buffer.
    pixel_buffer = np.ascontiguousarray(pixel_buffer)

    # Get ctypes representation of pixels
    pixels_prop_array = PropertyArrayRNA.from_address(id(image.pixels))
    # Get the PropertyRNA of the PropertyArrayRNA
    prop = pixels_prop_array.prop.contents
    # Blender checks these conditions internally to determine whether the prop's getlength function should be used, so
    # we will do the same.
    # The rna_ensure_property_multi_array_length code that gets run doesn't check pixels_prop_array.ptr.data, but the
    # code that would normally be executed if we didn't mess with the dimensions is rna_ensure_property_array_length,
    # which does check pixels_prop_array.ptr.data, so we include it in our checks here.
    if prop.magic == RNA_MAGIC and prop.getlength and pixels_prop_array.ptr.data:
        # Get the current arraydimension
        old_arraydimension = prop.arraydimension
        # Get the current getlength function and its address
        old_getlength = prop.getlength
        old_getlength_addr = ctypes.cast(old_getlength, ctypes.c_void_p).value

        # Create the Matrix that we're going to hack
        mat = Matrix()
        # Get the C representation of the Matrix
        c_mat = MatrixObject.from_address(id(mat))
        # Get the current pointed to datum, number of columns and number of rows
        mat_old_data = c_mat.matrix.contents
        mat_old_num_col = c_mat.num_col
        mat_old_num_row = c_mat.num_row

        c_int_matrix_columns = ctypes.c_int(matrix_columns)
        c_int_matrix_rows = ctypes.c_int(matrix_rows)

        # Define a custom getlength function that returns the total number of floats in the pixel_buffer and sets the
        # sizes of each dimension in the arr argument to those of the Matrix.
        def getlength_hack(_ptr, arr):
            arr[0] = c_int_matrix_columns
            arr[1] = c_int_matrix_rows
            return total_components  # ctypes handles converting the return value

        # Create a function pointer with the correct type for the function
        custom_getlength = PropArrayLengthGetFunc(getlength_hack)

        try:
            # Only now that we're inside the try block do we start changing the fields

            # Set up the Matrix:
            # Change the pointer to point to the start of the pixel_buffer's data
            c_mat.matrix.contents = ctypes.c_float.from_address(pixel_buffer.ctypes.data)

            # Set the number of columns and rows of the Matrix
            c_mat.num_col = matrix_columns
            c_mat.num_row = matrix_rows

            # Set up pixels prop_array:
            # Replace the getlength function with our own one
            prop.getlength = custom_getlength
            # Set the number of dimensions to match the matrix
            prop.arraydimension = 2

            # Blender will see that the number of dimensions and size of each dimension match and do a direct memcpy of
            # the data in mat into image.pixels
            image.pixels = mat
        finally:
            # ALWAYS set everything back to avoid memory leaks/corruption

            # Restore the pixels prop_array
            prop.arraydimension = old_arraydimension
            # Function pointers seem weird, setting prop.getlength to old_getlength seems to crash as it doesn't point
            # to the right memory for some reason. We can however create a void pointer to the address, cast it to
            # PropArrayLengthGetFunc and set prop.getlength to that.
            func_as_void = ctypes.c_void_p(old_getlength_addr)
            prop.getlength = ctypes.cast(func_as_void, PropArrayLengthGetFunc)

            # Restore the Matrix
            c_mat.matrix.contents = mat_old_data
            c_mat.num_col = mat_old_num_col
            c_mat.num_row = mat_old_num_row
    else:
        raise TypeError("{} pixels unexpectedly are not set up for using getlength, this shouldn't happen".format(image))
