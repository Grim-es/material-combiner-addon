from bpy.props import *
from .combiner_ops import *
from .packer import BinPacker
from ... import globs
from time import perf_counter


class Combiner(bpy.types.Operator):
    bl_idname = 'smc.combiner'
    bl_label = 'Create Atlas'
    bl_description = 'Combine materials'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    directory = StringProperty(maxlen=1024, default='', subtype='FILE_PATH', options={'HIDDEN'})
    filter_glob = StringProperty(default='', options={'HIDDEN'})
    cats = BoolProperty(default=False)
    data = None
    mats_uv = None
    structure = None

    def execute(self, context):
        if not self.data:
            self.invoke(context, None)
        timing_start = perf_counter()
        scn = context.scene
        scn.smc_save_path = self.directory
        add_images(self.structure)
        found_images = perf_counter()
        self.structure = BinPacker(get_size(scn, self.structure)).fit()
        size = (max([i['gfx']['fit']['x'] + i['gfx']['size'][0] for i in self.structure.values()]),
                max([i['gfx']['fit']['y'] + i['gfx']['size'][1] for i in self.structure.values()]))
        if any(dimension > 20000 for dimension in size):
            self.report({'ERROR'}, 'Output image size is too large')
            return {'FINISHED'}
        timing_packed = perf_counter()
        atlas = get_atlas(scn, self.structure, size)
        get_aligned_uv(scn, self.structure, atlas.size)
        assign_comb_mats(scn, self.data, self.mats_uv, atlas)
        clear_mats(scn, self.mats_uv)
        timing_atlased = perf_counter()
        print("DEBUG: Found images in {}s".format(found_images - timing_start))
        print("DEBUG: Packed atlas in {}s".format(timing_packed - found_images))
        print("DEBUG: Atlased materials in {}s".format(timing_atlased - timing_packed))
        bpy.ops.smc.refresh_ob_data()
        self.report({'INFO'}, 'Materials were combined.')
        return {'FINISHED'}

    def invoke(self, context, event):
        scn = context.scene
        bpy.ops.smc.refresh_ob_data()
        if self.cats:
            scn.smc_size = 'PO2'
            scn.smc_gaps = 0.0
        set_ob_mode(context.view_layer if globs.version > 0 else scn)
        self.data = get_data(scn.smc_ob_data)
        self.mats_uv = get_mats_uv(scn, self.data)
        clear_empty_mats(scn, self.data, self.mats_uv)
        set_root_mats(self.mats_uv)
        self.structure = get_structure(scn, self.data, self.mats_uv)
        if globs.version == 0:
            context.space_data.viewport_shade = 'MATERIAL'
        if (len(self.structure) == 1) and next(iter(self.structure.values()))['dup']:
            clear_duplicates(scn, self.structure)
            bpy.ops.smc.refresh_ob_data()
            self.report({'INFO'}, 'Duplicates were combined')
            return {'FINISHED'}
        elif not self.structure or (len(self.structure) == 1):
            bpy.ops.smc.refresh_ob_data()
            self.report({'ERROR'}, 'No unique materials selected')
            return {'FINISHED'}
        if event is not None:
            context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
