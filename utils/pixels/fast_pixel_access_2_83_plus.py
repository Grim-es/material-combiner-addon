import numpy as np
from .pixel_types import pixel_dtype

# The foreach_get and foreach_set methods for image.pixels were added in Blender 2.83


def get_pixels(image):
    pixels = image.pixels
    buffer = np.empty(len(pixels), dtype=pixel_dtype)
    pixels.foreach_get(buffer)
    return buffer


def set_pixels(img, buffer):
    # buffer must be C contiguous and flattened when writing
    img.pixels.foreach_set(buffer.ravel())
