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
import importlib
import os

from bpy.props import *
from bpy.app.handlers import persistent
from . import one_mat, uv_fixer, uv_splitter, gen_tex
from bpy.types import Panel, PropertyGroup, UIList, Operator, Scene, Material, Texture


importlib.reload(one_mat)
importlib.reload(uv_fixer)
importlib.reload(uv_splitter)
importlib.reload(gen_tex)


bl_info = {
    'name': 'Shotariya-don',
    'category': '3D View',
    'author': 'shotariya (shotariya#4269)',
    'location': 'View 3D > Tool Shelf > Shotariya-don',
    'description': 'Tool with some functions',
    'version': [1, 1, 2],
    'blender': (2, 79, 0),
    'wiki_url': '',
    'tracker_url': 'https://discordapp.com/users/275608234595713024',
    'warning': '',
}


class ShotariyaActions(Operator):
    bl_idname = 'shotariya.list_actions'
    bl_label = 'Action list'
    bl_description = ''
    bl_options = {'REGISTER'}

    action = EnumProperty(
        items=(
            ('GENERATE_MAT', 'Generate_mat', ''),
            ('ALL_MAT', 'All_mat', ''),
            ('CLEAR_MAT', 'Clear_mat', ''),
            ('GENERATE_TEX', 'Generate_tex', ''),
            ('ALL_TEX', 'All_tex', ''),
            ('CLEAR_TEX', 'Clear_tex', '')))

    def execute(self, context):
        return self.invoke(context, None)

    def invoke(self, context, event):
        scn = context.scene
        if self.action == 'GENERATE_MAT':
            scn.shotariya_mat.clear()
            scn.clear_mats = True
            scn.shotariya_mat_idx = 0
            for obj in scn.objects:
                if obj.type == 'MESH':
                    if not obj.data.uv_layers.active:
                        continue
                    for mat_slot in obj.material_slots:
                        if mat_slot:
                            mat = mat_slot.material
                            item = scn.shotariya_mat.add()
                            item.id = len(scn.shotariya_mat)
                            item.material = mat
                            item.name = item.material.name
                            item.material.to_combine = True
                            item.to_combine = item.material.to_combine
                            scn.shotariya_mat_idx = (len(scn.shotariya_mat)-1)
        if self.action == 'ALL_MAT':
            for obj in context.scene.objects:
                if obj.type == 'MESH':
                    if not obj.data.uv_layers.active:
                        continue
                    for mat_slot in obj.material_slots:
                        if mat_slot:
                            mat = mat_slot.material
                            mat.to_combine = True
                            scn.clear_mats = True
        if self.action == 'CLEAR_MAT':
            for obj in context.scene.objects:
                if obj.type == 'MESH':
                    if not obj.data.uv_layers.active:
                        continue
                    for mat_slot in obj.material_slots:
                        if mat_slot:
                            mat = mat_slot.material
                            mat.to_combine = False
                            scn.clear_mats = False
        if self.action == 'GENERATE_TEX':
            scn.shotariya_tex.clear()
            scn.clear_texs = True
            scn.shotariya_tex_idx = 0
            for obj in context.scene.objects:
                if obj.type == 'MESH':
                    if not obj.data.uv_layers.active:
                        continue
                    for mat_slot in obj.material_slots:
                        if mat_slot:
                            mat = mat_slot.material
                            tex_slot = False
                            for j in range(len(mat.texture_slots)):
                                if mat.texture_slots[j]:
                                    if mat.texture_slots[j].texture:
                                        if mat.use_textures[j]:
                                            tex_slot = mat.texture_slots[j]
                                            break
                            if tex_slot:
                                tex = tex_slot.texture
                                item = scn.shotariya_tex.add()
                                item.id = len(scn.shotariya_tex)
                                item.texture = tex
                                item.name = item.texture.name
                                item.texture.to_save = True
                                item.to_save = item.texture.to_save
                                scn.shotariya_tex_idx = (len(scn.shotariya_tex)-1)
        if self.action == 'ALL_TEX':
            for obj in scn.objects:
                if obj.type == 'MESH':
                    if not obj.data.uv_layers.active:
                        continue
                    for mat_slot in obj.material_slots:
                        if mat_slot:
                            mat = mat_slot.material
                            tex_slot = mat.texture_slots[0]
                            if tex_slot:
                                tex = tex_slot.texture
                                tex.to_save = True
                                scn.clear_texs = True
        if self.action == 'CLEAR_TEX':
            for obj in context.scene.objects:
                if obj.type == 'MESH':
                    if not obj.data.uv_layers.active:
                        continue
                    for mat_slot in obj.material_slots:
                        if mat_slot:
                            mat = mat_slot.material
                            tex_slot = mat.texture_slots[0]
                            if tex_slot:
                                tex = tex_slot.texture
                                tex.to_save = False
                                scn.clear_texs = False
        return {'FINISHED'}


class CombinedFolder(Operator):
    bl_idname = 'shotariya.combined_folder'
    bl_label = 'Select a Folder for Combined Texture'
    bl_description = ''
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    filepath = StringProperty(subtype='DIR_PATH')
    filter_glob = StringProperty(default='', options={'HIDDEN'})

    def execute(self, context):
        Scene.combined_path = self.filepath.rstrip(os.sep).lower()
        return {'FINISHED'}

    def invoke(self, context, event):
        scn = context.scene
        self.filepath = scn.combined_path + os.sep
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class MaterialsList(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        mat = item.material
        split = layout.row()
        split.prop(mat, 'name', emboss=False, text='', icon_value=layout.icon(mat))
        split.prop(mat, 'to_combine', text='')

    def invoke(self, context, event):
        pass


class MaterialsGroup(PropertyGroup):
    material = PointerProperty(
        name='Material',
        type=Material)


class TexFolder(Operator):
    bl_idname = 'shotariya.tex_folder'
    bl_label = 'Select a Folder for UVs / Diffuse Texture'
    bl_description = ''
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    filepath = StringProperty(subtype='DIR_PATH')
    filter_glob = StringProperty(default='', options={'HIDDEN'})

    def execute(self, context):
        Scene.tex_path = self.filepath.rstrip(os.sep).lower()
        return {'FINISHED'}

    def invoke(self, context, event):
        scn = context.scene
        self.filepath = scn.tex_path + os.sep
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class TexturesList(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        tex = item.texture
        split = layout.row()
        split.prop(tex, 'name', emboss=False, text='', icon_value=layout.icon(tex))
        split.prop(tex, 'to_save', text='')

    def invoke(self, context, event):
        pass


class TexturesGroup(PropertyGroup):
    texture = PointerProperty(
        name='Texture',
        type=Texture)


@persistent
def saved_folder(dummy):
    scn = bpy.context.scene
    if not scn.combined_path:
        if bpy.path.abspath('//'):
            scn.combined_path = bpy.path.abspath('//')
    if not scn.tex_path:
        if bpy.path.abspath('//'):
            scn.tex_path = bpy.path.abspath('//')


class ShotariyaMaterials(Panel):
    bl_label = 'Materials'
    bl_idname = 'shotariya.materials'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = 'shotariya'

    def draw(self, context):
        scn = context.scene
        layout = self.layout
        col = layout.column()
        col.label('Combiner', icon='FORCE_SMOKEFLOW')
        row = col.row()
        row.template_list('MaterialsList', 'materials_to_combine', scn, 'shotariya_mat',
                          scn, 'shotariya_mat_idx', rows=8, type='DEFAULT')
        row = layout.row()
        split = row.split(percentage=0.8, align=True)
        split.scale_y = 1.3
        if scn.shotariya_mat:
            gen_icon = 'VISIBLE_IPO_ON'
        else:
            gen_icon = 'VISIBLE_IPO_OFF'
        split.operator('shotariya.list_actions', icon=gen_icon, text='Generate materials list').action = 'GENERATE_MAT'
        if scn.clear_mats:
            clear_icon = 'CHECKBOX_HLT'
            clear_actiom = 'CLEAR_MAT'
        else:
            clear_icon = 'CHECKBOX_DEHLT'
            clear_actiom = 'ALL_MAT'
        split.operator('shotariya.list_actions', icon=clear_icon, text='').action = clear_actiom
        row = layout.row()
        split = row.split(percentage=0.8, align=True)
        split.scale_y = 1.3
        split.operator('shotariya.gen_mat', icon='SOLO_ON')
        if not scn.combined_path:
            combined_icon = 'NEWFOLDER'
        else:
            combined_icon = 'BOOKMARKS'
        split.operator('shotariya.combined_folder', text='', icon=combined_icon)


class ShotariyaTextures(Panel):
    bl_label = 'Textures'
    bl_idname = 'shotariya.textures'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = 'shotariya'

    def draw(self, context):
        scn = context.scene
        layout = self.layout
        col = layout.column()
        col.label('Retexturer', icon='MOD_SMOKE')
        row = col.row()
        row.template_list('TexturesList', 'textures_to_combine', scn, 'shotariya_tex',
                          scn, 'shotariya_tex_idx', rows=8, type='DEFAULT')
        row = layout.row()
        split = row.split(percentage=0.8, align=True)
        split.scale_y = 1.3
        if scn.shotariya_tex:
            gen_icon = 'VISIBLE_IPO_ON'
        else:
            gen_icon = 'VISIBLE_IPO_OFF'
        split.operator('shotariya.list_actions', icon=gen_icon, text='Generate textures list').action = 'GENERATE_TEX'
        if scn.clear_texs:
            clear_icon = 'CHECKBOX_HLT'
            clear_actiom = 'CLEAR_TEX'
        else:
            clear_icon = 'CHECKBOX_DEHLT'
            clear_actiom = 'ALL_TEX'
        split.operator('shotariya.list_actions', icon=clear_icon, text='').action = clear_actiom
        col = layout.column()
        split = col.split(percentage=0.8, align=True)
        split.scale_y = 1.3
        split.operator('shotariya.gen_tex', icon='FILE_IMAGE')
        if not scn.tex_path:
            tex_icon = 'NEWFOLDER'
        else:
            tex_icon = 'BOOKMARKS'
        split.operator('shotariya.tex_folder', text='', icon=tex_icon)
        col.separator()


class ShotariyaUVs(Panel):
    bl_label = 'UVs'
    bl_idname = 'shotariya.uvs'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = 'shotariya'

    def draw(self, context):
        scn = context.scene
        layout = self.layout
        col = layout.column()
        col.label('Mover', icon='DRIVER')
        col.scale_y = 1.3
        col.operator('shotariya.uv_fixer', icon='ROTATE')
        col.separator()
        col.label('Packer', icon='NLA_PUSHDOWN')
        split = col.split(percentage=0.8, align=True)
        split.scale_y = 1.3
        split.operator('shotariya.uv_splitter', icon='MOD_DECIM')
        split.prop(scn, 'uv_size', text='')
        col.separator()


classes = (
    ShotariyaMaterials,
    ShotariyaTextures,
    ShotariyaUVs,
    CombinedFolder,
    MaterialsList,
    MaterialsGroup,
    TexFolder,
    TexturesList,
    TexturesGroup,
    ShotariyaActions,
    one_mat.GenMat,
    uv_fixer.FixUV,
    uv_splitter.SplitUV,
    gen_tex.GenTex
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    Scene.shotariya_mat = CollectionProperty(type=MaterialsGroup)
    Scene.shotariya_mat_idx = IntProperty(default=0)
    Material.to_combine = BoolProperty(name='Add material to combine', default=False)
    Scene.clear_mats = BoolProperty(name='Clear materials checkbox', default=True)
    Scene.combined_path = StringProperty(default='')
    Scene.shotariya_tex = CollectionProperty(type=TexturesGroup)
    Scene.shotariya_tex_idx = IntProperty(default=0)
    Texture.to_save = BoolProperty(name='Add textures to save', default=False)
    Scene.clear_texs = BoolProperty(name='Clear textures checkbox', default=True)
    Scene.tex_path = StringProperty(default='')
    Scene.uv_size = IntProperty(default=1, min=1, max=10)
    if saved_folder not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(saved_folder)
    if saved_folder not in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.append(saved_folder)
    if saved_folder not in bpy.app.handlers.scene_update_post:
        bpy.app.handlers.scene_update_post.append(saved_folder)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del Scene.shotariya_mat
    del Scene.shotariya_mat_idx
    del Material.to_combine
    del Scene.clear_mats
    del Scene.combined_path
    del Scene.shotariya_tex
    del Scene.shotariya_tex_idx
    del Texture.to_save
    del Scene.clear_texs
    del Scene.tex_path
    del Scene.uv_size
    if saved_folder in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(saved_folder)
    if saved_folder in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.remove(saved_folder)
    if saved_folder in bpy.app.handlers.scene_update_post:
        bpy.app.handlers.scene_update_post.remove(saved_folder)


if __name__ == '__main__':
    register()
