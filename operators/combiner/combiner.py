import bpy
from bpy.props import *

from .combiner_ops import *
from .packer import BinPacker
from ... import globs


class Combiner(bpy.types.Operator):
    bl_idname = 'smc.combiner'
    bl_label = 'Create Atlas'
    bl_description = 'Combine materials'
    bl_options = {'UNDO', 'INTERNAL'}

    directory = StringProperty(maxlen=1024, default='', subtype='FILE_PATH', options={'HIDDEN'})
    filter_glob = StringProperty(default='', options={'HIDDEN'})
    cats = BoolProperty(default=False)
    data = None
    mats_uv = None
    structure = None

    def execute(self, context: bpy.types.Context) -> Set[str]:
        if not self.data:
            self.invoke(context, None)
        scn = context.scene
        if self.directory:
            scn.smc_save_path = self.directory
        else:
            scn.smc_save_path = bpy.path.abspath("//")
        self.structure = BinPacker(get_size(scn, self.structure)).fit()

        size = get_atlas_size(self.structure)
        atlas_size = calculate_adjusted_size(scn, size)

        if max(atlas_size, default=0) > 20000:
            self.report({'ERROR'}, 'The output image size of {0}x{1}px is too large'.format(*atlas_size))
            return {'FINISHED'}

        atlas = get_atlas(scn, self.structure, atlas_size)
        align_uvs(scn, self.structure, atlas.size, size)
        comb_mats = get_comb_mats(scn, atlas, self.mats_uv)
        assign_comb_mats(scn, self.data, comb_mats)
        clear_mats(scn, self.mats_uv)
        bpy.ops.smc.refresh_ob_data()
        self.report({'INFO'}, 'Materials were combined')
        return {'FINISHED'}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> Set[str]:
        scn = context.scene
        bpy.ops.smc.refresh_ob_data()

        if self.cats:
            scn.smc_size = 'PO2'
            scn.smc_gaps = 0

        set_ob_mode(context.view_layer if globs.is_blender_2_80_or_newer else scn, scn.smc_ob_data)
        self.data = get_data(scn.smc_ob_data)
        self.mats_uv = get_mats_uv(scn, self.data)
        clear_empty_mats(scn, self.data, self.mats_uv)
        get_duplicates(self.mats_uv)
        self.structure = get_structure(scn, self.data, self.mats_uv)

        if globs.is_blender_2_79_or_older:
            context.space_data.viewport_shade = 'MATERIAL'

        if len(self.structure) == 1 and next(iter(self.structure.values()))['dup']:
            clear_duplicates(scn, self.structure)
            return self._return_with_message('INFO', 'Duplicates were combined')
        elif not self.structure or len(self.structure) == 1:
            return self._return_with_message('ERROR', 'No unique materials selected')
        if event is not None:
            context.window_manager.fileselect_add(self)

        return {'RUNNING_MODAL'}

    def _return_with_message(self, message_type: str, message: str) -> Set[str]:
        bpy.ops.smc.refresh_ob_data()
        self.report({message_type}, message)
        return {'FINISHED'}
