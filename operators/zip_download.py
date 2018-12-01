import bpy
import os
from bpy.props import *
from io import BytesIO
from zipfile import ZipFile
from urllib.request import urlopen


class OpenBrowser(bpy.types.Operator):
    bl_idname = 'smc.zip_download'
    bl_label = 'Download & Extract zip'

    link = StringProperty(default='')

    def execute(self, context):
        assets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, 'assets')
        if not os.path.exists(assets_path):
            os.makedirs(assets_path)
        resp = urlopen(self.link)
        zipfile = ZipFile(BytesIO(resp.read()))
        zipfile.extractall(assets_path)
        zipfile.close()
        self.report({'INFO'}, 'Download Complete')
        return {'FINISHED'}
