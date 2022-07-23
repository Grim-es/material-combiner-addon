import bpy
from bpy.types import Image

import numpy as np

from . import pixel_access
from .pixel_types import pixel_dtype
from ..type_hints import PixelBuffer, Size, Pixel, CornerOrBox
from ...globs import debug_print

# A 'pixel buffer' is a single precision float type numpy array, viewed in the 3D shape
# (height, width, channels), used to store data representing image pixels.

linear_colorspaces = {'Linear', 'Non-Color', 'Raw'}
supported_colorspaces = linear_colorspaces | {'sRGB'}


def new_pixel_buffer(size: Size, color: Pixel = (0.0, 0.0, 0.0, 0.0), read_only_rectangle=False, convert_linear_to_srgb=True) -> PixelBuffer:
    """Create a new blank pixel buffer, filled with a single linear color.

    A 'pixel buffer' is a single precision float type numpy array, viewed in the 3D shape
    (height, width, channels), used to store data representing image pixels.

    The number of channels is determined based on the fill color.
    Default fill color is transparent black.

    :return: a new pixel buffer ndarray
    """
    width, height = size
    # rgba
    channels = len(color)
    # color could be an ndarray, but len only counts the length of the first dimension so the dimensions need to be
    # checked too
    if isinstance(color, np.ndarray) and len(color.shape) != 1:
        raise TypeError("color must be one dimensional, but has shape {}".format(color.shape))
    if channels > 4 or channels == 0:
        raise TypeError("A color can have between 1 and 4 (inclusive) components, but found {} in {}".format(channels, color))
    color = np.array(color)
    # Colors are in scene linear colorspace, if we want them to look the same in an sRGB image, we must convert them.
    if convert_linear_to_srgb:
        print("Converting color {} for sRGB".format(color))
        color = color_convert_linear_to_srgb(color)
        print("Converted color to {}".format(color))
    if read_only_rectangle:
        # Create a 1x1 pixel_buffer, and then broadcast it to the specified shape, this creates a read-only
        # pixel buffer that acts like it is the full size, but every pixel shares the same memory
        buffer_base = np.array([[color]], dtype=pixel_dtype)
        buffer = np.broadcast_to(buffer_base, (height, width, channels))
    else:
        buffer = np.full((height, width, channels), fill_value=color, dtype=pixel_dtype)
    return buffer


def is_read_only_rectangle(buffer: PixelBuffer) -> bool:
    base = buffer.base
    return (not buffer.flags.writeable  # read-only means it's not writeable
            and base is not None  # it must have a base array
            and len(base.shape) == 3  # the base array must be 3-dimensional
            and base.shape[0] == 1  # the height must be 1px
            and base.shape[1] == 1  # the width must be 1px
            and 1 <= base.shape[2] <= 4)  # the number of channels must be 1 to 4 inclusive


def get_base_if_read_only_rectangle(buffer: PixelBuffer) -> PixelBuffer:
    if is_read_only_rectangle(buffer):
        return buffer.base
    else:
        return buffer


def get_pixel_buffer(image: Image, target_colorspace='sRGB') -> PixelBuffer:
    """Create a new pixel buffer filled with the pixels of the specified image.

    A 'pixel buffer' is a single precision float type numpy array, viewed in the 3D shape
    (image.size[1], image.size[0], image.channels), used to store data representing image pixels.

    If the target_colorspace doesn't match the image's colorspace, the pixels are converted such that they appear the
    same in the target_colorspace as they did in the image's colorspace.

    :return: a new pixel buffer containing a copy of the image's pixels"""
    width, height = image.size
    channels = image.channels
    buffer = pixel_access.get_pixels(image)
    # View the buffer in a shape that better represents the data
    buffer.shape = (height, width, channels)

    # Pixels are always read raw, meaning that changing the colorspace of the image has no effect on the pixels,
    # but if we want to combine an X colorspace image into a Y colorspace atlas such that the X colorspace image appears
    # the same when viewed in Y colorspace, we need to pre-convert it from X colorspace to Y colorspace.
    img_color_space = image.colorspace_settings.name
    if target_colorspace == 'sRGB':
        if img_color_space == 'sRGB':
            return buffer
        elif img_color_space in linear_colorspaces:
            # Need to convert from Linear to sRGB
            buffer_convert_linear_to_srgb(buffer)
            return buffer
        else:
            raise TypeError("Unsupported image colorspace {} for {}. Must be in {}.".format(img_color_space, image, supported_colorspaces))
    elif target_colorspace in linear_colorspaces:
        if img_color_space in linear_colorspaces:
            return buffer
        elif img_color_space == 'sRGB':
            # Need to convert from sRGB to linear
            buffer_convert_srgb_to_linear(buffer)
            return buffer
    else:
        raise TypeError("Unsupported atlas colorspace {}. Must be in {}".format(target_colorspace, supported_colorspaces))


# Copy the image, resize the copy and then get the pixel buffer, the copied image is then destroyed
# The alternative would be to resize the passed in image and then reload it afterwards, but if the passed in image was
# dirty, then those dirty changes would be lost.
def get_resized_pixel_buffer(image: Image, size: Size) -> PixelBuffer:
    """Create a new pixel buffer filled with the pixels of the specified image after resizing it (does not change the
     original image).

     size must be a tuple-like object where the first index is the new width and the second index is the new height.

     :return: a new pixel buffer containing a copy of the resized image's pixels"""
    # Copy the input image
    copy = image.copy()
    # Scale (resize) the copy
    copy.scale(size[0], size[1])
    # Get the pixel buffer for the scaled copy
    buffer = get_pixel_buffer(copy)
    # Delete the scaled copy
    bpy.data.images.remove(copy)
    return buffer


def write_pixel_buffer(image: Image, buffer: PixelBuffer):
    """Write a pixel buffer's pixels to an existing image.

    The image must have the same width, height and number of channels as the buffer."""
    width, height = image.size
    image_shape = (height, width, image.channels)
    if buffer.shape == image_shape:
        pixel_access.set_pixels(image, buffer)
    else:
        raise RuntimeError("Buffer shape {} does not match image shape {}".format(buffer.shape, image_shape))


def buffer_to_image(buffer: PixelBuffer, *, name: str) -> Image:
    """Write a pixel buffer's pixels to a new image.

    :return: the newly created image with pixels set to the pixel buffer."""
    image = bpy.data.images.new(name, buffer.shape[1], buffer.shape[0], alpha=buffer.shape[2] == 4)
    write_pixel_buffer(image, buffer)
    return image


def color_convert_linear_to_srgb(color_array):
    """Convert a linear colorspace color such that it will look the same in an sRGB colorspace.

    Converts in-place if the input color_array is already an ndarray of the correct type.

    :return:Input linear color array converted to look the same in sRGB"""
    color_as_array = np.asarray(color_array, dtype=pixel_dtype)
    # View the array in the shape of a pixel buffer
    color_as_array.shape = (1, 1, -1)
    buffer_convert_linear_to_srgb(color_as_array)
    # Reshape the array back to flat
    color_as_array.shape = -1
    return color_as_array


def color_convert_srgb_to_linear(color_array):
    """Convert an sRGB colorspace color such that it will look the same in a linear colorspace

    Converts in-place if the input color_array is already an ndarray of the correct type.

    :return:Input sRGB color array converted to look the same in linear"""
    color_as_array = np.asarray(color_array, dtype=pixel_dtype)
    # View the array in the shape of a pixel buffer
    color_as_array.shape = (1, 1, -1)
    buffer_convert_srgb_to_linear(color_as_array)
    # Reshape the array back to flat
    color_as_array.shape = -1
    return color_as_array


# Uses the same conversion as Blender's node_color.h
def buffer_convert_linear_to_srgb(buffer: PixelBuffer):
    """In-place convert a linear colorspace pixel buffer such that it will look the same in an sRGB colorspace"""
    # If the buffer is a read-only rectangle, get the base array so that it can be modified
    buffer = get_base_if_read_only_rectangle(buffer)

    # Alpha is always linear, so get a view of only RGB.
    rgb_only_view = buffer[:, :, :3]

    # Mask of all small values
    is_small = rgb_only_view < 0.0031308

    # Array of only the small values
    small_rgb = rgb_only_view[is_small]

    # Slightly faster than:
    # rgb_only_view[is_small] = np.where(small_rgb < 0.0, 0, small_rgb * 12.92)
    np.maximum(small_rgb, 0, out=small_rgb)
    small_rgb *= 12.92
    rgb_only_view[is_small] = small_rgb

    # New variable name for clarity
    is_not_small = np.invert(is_small, out=is_small)

    # In-place equivalent of:
    # rgb_only_view[is_not_small] = 1.055 * (rgb_only_view[is_not_small] ** (1.0 / 2.4)) - 0.055
    large_rgb = rgb_only_view[is_not_small]
    large_rgb **= 1.0/2.4
    large_rgb *= 1.055
    large_rgb -= 0.055
    rgb_only_view[is_not_small] = large_rgb


# Uses the same conversion as Blender's node_color.h
def buffer_convert_srgb_to_linear(buffer: PixelBuffer):
    """In-place convert an sRGB colorspace pixel buffer such that it will look the same in a linear colorspace"""
    # If the buffer is a read-only rectangle, get the base array so that it can be modified
    buffer = get_base_if_read_only_rectangle(buffer)

    # Alpha is always linear, so get a view of only RGB.
    rgb_only_view = buffer[:, :, :3]

    # Mask of all small values
    is_small = rgb_only_view < 0.04045

    # Array of only the small values
    small_rgb = rgb_only_view[is_small]

    # Slightly faster than:
    # rgb_only_view[is_small] = np.where(small_rgb < 0.0, 0, small_rgb / 12.92)
    np.maximum(small_rgb, 0, out=small_rgb)
    small_rgb /= 12.92
    rgb_only_view[is_small] = small_rgb

    # New variable name for clarity
    is_not_small = np.invert(is_small, out=is_small)

    # In-place equivalent of:
    # rgb_only_view[is_not_small] = ((rgb_only_view[is_not_small] + 0.055) / 1.055) ** 2.4
    large_rgb = rgb_only_view[is_not_small]
    large_rgb += 0.055
    large_rgb /= 1.055
    large_rgb **= 2.4
    rgb_only_view[is_not_small] = large_rgb


def pixel_buffer_paste(target_buffer: PixelBuffer, source_buffer: PixelBuffer, corner_or_box: CornerOrBox):
    """Paste pixels from a source pixel buffer into the target pixel buffer.

    Where the source is to be pasted is specified via a tuple-like set of pixel coordinates specifying either a top left
     corner or a box. Note that these coordinates use the coordinate system of Pillow, whereby (0,0) is the top left of
      an image, whereas in Blender, (0,0) is considered the bottom left of an image.

    A corner is specified as (left, upper) and a box is specified as (left, upper, right, lower). Both must be
     tuple-like or list-like.

    If a box is specified, the width and height of the box must match the source_buffer.
    """
    # box coordinates treat (0,0) as top left, but bottom left is (0,0) in blender, so view the buffer with flipped
    # y-axis
    target_buffer = np.flipud(target_buffer)
    if isinstance(source_buffer, np.ndarray):
        if len(source_buffer.shape) != 3:
            raise TypeError("source buffer could not be parsed for pasting")
    else:
        raise TypeError("source buffer could not be parsed for pasting")

    # box coordinates treat (0,0) as top left, but bottom left is (0,0) in blender, so view the buffer with flipped
    # y-axis
    source_buffer = np.flipud(source_buffer)
    # Parse a corner into a box
    if len(corner_or_box) == 2:
        # Only the top left corner to place the source buffer has been set, we will figure out the bottom right
        # corner
        left, upper = corner_or_box
        right = left + source_buffer.shape[1]
        lower = upper + source_buffer.shape[0]
    elif len(corner_or_box) == 4:
        left, upper, right, lower = corner_or_box
    else:
        raise TypeError("corner or box must be either a 2-tuple or 4-tuple, but was: {}".format(corner_or_box))

    if target_buffer.shape[-1] >= source_buffer.shape[-1]:
        # Fit the box to the image
        # Remember that box corners are cartesian coordinates where (0,0) is the top left corner of the top left pixel
        # and (1,1) is the bottom right corner of the top left pixel
        buffer_height, buffer_width, _buffer_channels = target_buffer.shape
        fit_left = max(left, 0)
        fit_upper = max(upper, 0)
        fit_right = min(right, buffer_width)
        fit_lower = min(lower, buffer_height)
        if fit_left != left or fit_upper != upper or fit_right != right or fit_lower != lower:
            debug_print('DEBUG: Image to be pasted did not fit into target image, {} -> {}'
                        .format((left, upper, right, lower), (fit_left, fit_upper, fit_right, fit_lower)))

        # If the pasted buffer can extend outside the source image, we need to figure out the area which fits within
        # the source image
        source_left = fit_left - left
        source_upper = fit_upper - upper
        source_right = source_buffer.shape[1] - right + fit_right
        source_lower = source_buffer.shape[0] - lower + fit_lower
        num_source_channels = source_buffer.shape[2]
        debug_print("DEBUG: Pasting into box {} of target from box {} of source".format(
            (fit_left, fit_upper, fit_right, fit_lower), (source_left, source_upper, source_right, source_lower)))
        target_buffer[fit_upper:fit_lower, fit_left:fit_right, :num_source_channels] = source_buffer[source_upper:source_lower, source_left:source_right]
    else:
        raise TypeError("Pixels in source have more channels than pixels in target, they cannot be pasted")
