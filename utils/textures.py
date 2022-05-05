# Material textures are only in Blender 2.79 and older, these functions are not used in newer Blender versions

def get_texture(mat):
    return next((mat.texture_slots[slot_idx].texture for slot_idx in range(len(mat.texture_slots))
                 if (mat.texture_slots[slot_idx] is not None) and mat.use_textures[slot_idx]), None)


def get_image(tex):
    return tex.image if tex and hasattr(tex, 'image') and tex.image else None
