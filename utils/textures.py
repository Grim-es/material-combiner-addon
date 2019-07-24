import bpy


def get_texture(mat):
    return next((mat.texture_slots[slot_idx].texture for slot_idx in range(len(mat.texture_slots))
                 if (mat.texture_slots[slot_idx] is not None) and mat.use_textures[slot_idx]), None)


def get_textures(mat):
    return {slot_idx: mat.texture_slots[slot_idx].texture for slot_idx in range(len(mat.texture_slots))
            if (mat.texture_slots[slot_idx] is not None) and mat.use_textures[slot_idx]}
