import bpy


def get_materials(ob):
    return [mat_slot.material for mat_slot in ob.material_slots]


def get_texture(mat):
    return next((mat.texture_slots[slot_idx].texture for slot_idx in range(len(mat.texture_slots))
                 if (mat.texture_slots[slot_idx] is not None) and mat.use_textures[slot_idx]), None)


def get_textures(mat):
    return {slot_idx: mat.texture_slots[slot_idx].texture for slot_idx in range(len(mat.texture_slots))
            if (mat.texture_slots[slot_idx] is not None) and mat.use_textures[slot_idx]}


def get_diffuse(mat):
    return (int(mat.diffuse_color.r * 255),
            int(mat.diffuse_color.g * 255),
            int(mat.diffuse_color.b * 255))
