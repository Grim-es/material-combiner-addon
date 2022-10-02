import numpy as np

from .pixels.pixel_buffer import (color_convert_linear_to_srgb, pixel_dtype, color_convert_srgb_to_linear,
                                  linear_colorspaces, supported_colorspaces)


# Note that in Blender 2.79, .is_dirty is always True for BLANK GENERATED images, so this will always return False there
def is_single_colour_generated(img):
    """:return:True if the img argument is a generated image of a single color that doesn't have any pending changes"""
    return img.source == 'GENERATED' and not img.is_dirty and img.generated_type == 'BLANK'


def is_image_too_large(width, height, components_per_pixel=4) -> bool:
    # The total length of an image's pixels array cannot exceed the signed integer maximum, which is usually
    # 2147483647 (for 32-bit signed integers). For a square image, this maximum is first exceeded by a
    # 23171x23171 pixel image.
    # If this maximum is exceeded, the length of the array will overflow in Blender's code, leading to an error
    # message like "TypeError: expected sequence size -2147483648, got -2147483648" when trying to set the
    # image's pixels.
    # Width * height * r,g,b,a
    return (width * height * components_per_pixel) > np.iinfo(np.intc).max


# Convert a single color generated image to a color
# The image's generated color is in linear, if the image is in sRGB, the color must be converted
def single_color_generated_to_color(img, diffuse_to_multiply=None, target_colorspace='sRGB'):
    generated_color = np.array(img.generated_color, dtype=pixel_dtype)
    diffuse_to_multiply_arr = np.array(diffuse_to_multiply, dtype=pixel_dtype) if diffuse_to_multiply else None
    image_colorspace = img.colorspace_settings.name
    if target_colorspace == 'sRGB':
        if image_colorspace == 'sRGB':
            # linear values from image color are to be kept as is, only the color needs converting since the diffuse
            # color needs converting
            if diffuse_to_multiply:
                return generated_color * color_convert_linear_to_srgb(diffuse_to_multiply_arr)
            else:
                return generated_color
        elif image_colorspace in linear_colorspaces:
            if diffuse_to_multiply:
                return color_convert_linear_to_srgb(generated_color * diffuse_to_multiply_arr)
            else:
                return color_convert_linear_to_srgb(generated_color)
    elif target_colorspace in linear_colorspaces:
        if image_colorspace == 'sRGB':
            if diffuse_to_multiply:
                return color_convert_srgb_to_linear(generated_color) * diffuse_to_multiply_arr
            else:
                return color_convert_srgb_to_linear(generated_color)
        elif image_colorspace in linear_colorspaces:
            if diffuse_to_multiply:
                return generated_color * diffuse_to_multiply_arr
            else:
                return generated_color
    else:
        raise TypeError("Unsupported target colorspace '{}'. The target colorspace must be one of: {}".format(
            target_colorspace, supported_colorspaces))
    raise TypeError("Unsupported colorspace '{}' for image \"{}\". The image's colorspace must be changed to one"
                    " of: {}".format(image_colorspace, img.name, supported_colorspaces))


def save_generated_image_to_file(image, filepath, file_format=None):
    """Save a generated image to a filepath, this will set the filepath of the image and cause the
    image source to be changed to 'FILE' instead of 'GENERATED'"""
    # Note that setting image.filepath and/or image.source = 'FILE' can't be done, otherwise it will reset the image
    image.filepath_raw = filepath
    if file_format:
        image.file_format = file_format
    image.save()
