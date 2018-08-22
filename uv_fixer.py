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
import time


class FixUV(bpy.types.Operator):
    bl_idname = 'shotariya.uv_fixer'
    bl_label = 'Move UVs closer to bounds'
    bl_description = ''
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        start_time = time.time()
        scene = bpy.context.scene
        for obj in scene.objects:
            if obj.type == 'MESH':
                if not obj.data.uv_layers.active or not obj.hode:
                    continue
                for face in obj.data.polygons:
                    try:
                        face_coords = [obj.data.uv_layers.active.data[loop_idx].uv for loop_idx in face.loop_indices]
                        x = 0
                        y = 0
                        xi = min([x.x for x in face_coords])
                        yi = min([y.y for y in face_coords])
                        while xi >= 0.999:
                            xi -= 1
                            x -= 1
                        while xi < 0:
                            xi += 1
                            x += 1
                        while yi >= 0.999:
                            yi -= 1
                            y -= 1
                        while yi < 0:
                            yi += 1
                            y += 1
                        if x != 0:
                            for i in face_coords:
                                i.x += x
                        if y != 0:
                            for i in face_coords:
                                i.y += y
                    except:
                        print(obj.name + 'Has no UV map')
        print('{} seconds passed'.format(time.time() - start_time))
        self.report({'INFO'}, 'UVs were fixed.')
        return{'FINISHED'}
