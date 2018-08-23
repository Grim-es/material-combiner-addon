# MIT License

# Copyright (c) 2018 shotariya

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import bpy
import bmesh
import math
import time


class SplitUV(bpy.types.Operator):
    bl_idname = 'shotariya.uv_splitter'
    bl_label = 'Pack UVs by splitting mesh'
    bl_description = ''
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def split(self, uv_size, obj, cicled):
        bpy.ops.shotariya.uv_fixer()
        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)
        uv_lay = bm.loops.layers.uv.active

        x_loops = {}
        for face in bm.faces:
            for loop in face.loops:
                if face in x_loops:
                    x_loops[face].append(loop)
                else:
                    x_loops[face] = [loop]

        for face, loops in x_loops.items():
            verts_to_separate_x = []
            loops_len = len(loops)
            for id, loop in enumerate(loops):
                n = id + 1
                if n == loops_len:
                    n = 0
                n_loop = loops[n]
                uv_vert = loop[uv_lay].uv
                n_uv_vert = n_loop[uv_lay].uv
                vert = loop.vert
                n_vert = n_loop.vert
                edge = loop.edge
                edge_len_x = abs(n_uv_vert.x - uv_vert.x)
                if (uv_vert.x > uv_size) and (n_uv_vert.x > uv_size):
                    continue
                else:
                    if (uv_vert.x <= uv_size) and (n_uv_vert.x <= uv_size):
                        continue
                    else:
                        if uv_vert.x < uv_size:
                            cut = ((uv_size - uv_vert.x) / edge_len_x)
                            for e_vert in edge.verts:
                                if e_vert == vert:
                                    verts_to_separate_x.append(bmesh.utils.edge_split(edge, e_vert, cut)[1])
                        elif uv_vert.x == uv_size:
                            verts_to_separate_x.append(vert)
                        if n_uv_vert.x < uv_size:
                            cut = ((uv_size - n_uv_vert.x) / edge_len_x)
                            for e_vert in edge.verts:
                                if e_vert == n_vert:
                                    verts_to_separate_x.append(bmesh.utils.edge_split(edge, e_vert, cut)[1])
                        elif n_uv_vert.x == uv_size:
                            verts_to_separate_x.append(n_vert)
            if len(verts_to_separate_x) == 2:
                try:
                    bmesh.utils.face_split(face, verts_to_separate_x[0], verts_to_separate_x[1])[0]
                except:
                    continue
        bm.to_mesh(mesh)
        bm.free()

        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)
        uv_lay = bm.loops.layers.uv.active

        y_loops = {}
        for face in bm.faces:
            for loop in face.loops:
                if face in y_loops:
                    y_loops[face].append(loop)
                else:
                    y_loops[face] = [loop]

        for face, loops in y_loops.items():
            verts_to_separate_y = []
            loops_len = len(loops)
            for id, loop in enumerate(loops):
                n = id + 1
                if n == loops_len:
                    n = 0
                n_loop = loops[n]
                uv_vert = loop[uv_lay].uv
                n_uv_vert = n_loop[uv_lay].uv
                vert = loop.vert
                n_vert = n_loop.vert
                edge = loop.edge
                edge_len_y = abs(n_uv_vert.y - uv_vert.y)
                if (uv_vert.y > uv_size) and (n_uv_vert.y > uv_size):
                    continue
                else:
                    if (uv_vert.y <= uv_size) and (n_uv_vert.y <= uv_size):
                        continue
                    else:
                        if uv_vert.y < uv_size:
                            cut = ((uv_size - uv_vert.y) / edge_len_y)
                            for e_vert in edge.verts:
                                if e_vert == vert:
                                    verts_to_separate_y.append(bmesh.utils.edge_split(edge, e_vert, cut)[1])
                        elif uv_vert.y == uv_size:
                            verts_to_separate_y.append(vert)
                        if n_uv_vert.y < uv_size:
                            cut = ((uv_size - n_uv_vert.y) / edge_len_y)
                            for e_vert in edge.verts:
                                if e_vert == n_vert:
                                    verts_to_separate_y.append(bmesh.utils.edge_split(edge, e_vert, cut)[1])
                        elif n_uv_vert.y == uv_size:
                            verts_to_separate_y.append(n_vert)
            if len(verts_to_separate_y) == 2:
                try:
                    bmesh.utils.face_split(face, verts_to_separate_y[0], verts_to_separate_y[1])[0]
                except:
                    continue
        bm.to_mesh(mesh)
        bm.free()

        for face in obj.data.polygons:
            x = 0
            y = 0
            if face.loop_indices > 0:
                face_coords = [obj.data.uv_layers.active.data[loop_idx].uv for loop_idx in face.loop_indices]
                xi = min([x.x for x in face_coords])
                yi = min([y.y for y in face_coords])
                while xi >= 0.999:
                    xi -= 1
                    x -= 1
                while yi >= 0.999:
                    yi -= 1
                    y -= 1
                if x != 0:
                    for i in face_coords:
                        i.x += x
                if y != 0:
                    for i in face_coords:
                        i.y += y
        for face in obj.data.polygons:
            if face.loop_indices > 0:
                face_coords = [obj.data.uv_layers.active.data[loop_idx].uv for loop_idx in face.loop_indices]
                xi = max([x.x for x in face_coords])
                yi = max([y.y for y in face_coords])
                if (xi > 1) or (yi > 1):
                    if cicled < 100:
                        return True
        for uv in obj.data.uv_layers:
            for vert in range(len(uv.data) - 1):
                if math.isnan(uv.data[vert].uv.x):
                    uv.data[vert].uv.x = 0
                if math.isnan(uv.data[vert].uv.y):
                    uv.data[vert].uv.y = 0

    def execute(self, context):
        start_time = time.time()
        scn = context.scene
        uv_size = scn.uv_size
        for obj in scn.objects:
            if obj.type == 'MESH':
                if not obj.data.uv_layers.active or obj.hide:
                    continue
                scn.objects.active = obj
                cicled = 0
                while self.split(uv_size, obj, cicled):
                    cicled += 1
        print('{} seconds passed'.format(time.time() - start_time))
        self.report({'INFO'}, 'UVs packed.')
        return{'FINISHED'}
