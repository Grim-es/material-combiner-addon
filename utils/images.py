import numpy as np

from .pixels.pixel_buffer import (color_convert_linear_to_srgb, pixel_dtype, color_convert_srgb_to_linear,
                                  linear_colorspaces, supported_colorspaces)


def is_single_colour_generated(img):
    """:return:True if the img argument is a generated image of a single color that doesn't have any pending changes"""
    return img.source == 'GENERATED' and not img.is_dirty and img.generated_type == 'BLANK'


# The generated color is in linear, if the image is in sRGB, the color must be converted
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
