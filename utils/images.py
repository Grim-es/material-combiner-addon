from typing import Union

import bpy


def get_image(tex: bpy.types.Texture) -> bpy.types.Image:
    return tex.image if tex and hasattr(tex, 'image') and tex.image else None


def get_packed_file(image: Union[bpy.types.Image, None]) -> Union[bpy.types.PackedFile, None]:
    if image and not image.packed_file:
        image.pack()
    return image.packed_file if image and image.packed_file else None
