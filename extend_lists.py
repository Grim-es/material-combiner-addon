import bpy
import os
from . icons import get_icon_id, get_img_icon_id


class ObDataItems(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row()
        if item.data_type == 0:
            row.label(item.ob.name, icon='VIEW3D')
            if item.used:
                used_text = 'Deselect All'
            else:
                used_text = 'Select All'
            row = row.row()
            row.alignment = 'RIGHT'
            row.operator('smc.combine_switch', text=used_text, emboss=False).list_id = index
        elif item.data_type == 1:
            row.separator()
            row = row.row(align=True)
            row.label(text='', icon_value=item.mat.preview.icon_id)
            row.prop(item, 'layer', text='{}'
                     .format(item.mat.name))
            if item.used:
                used_icon = 'FILE_TICK'
            else:
                used_icon = 'LAYER_USED'
            row.operator('smc.combine_switch', text='', icon=used_icon).list_id = index

    def invoke(self, context, event):
        pass


class ImageItems(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row()
        if item.img_type == 0:
            item_img_icon = get_icon_id('texture')
        elif item.img_type == 2:
            item_img_icon = get_icon_id('diffuse')
        else:
            if os.path.isfile(item.img_path):
                item_img_icon = get_img_icon_id(item.img_name, item.img_path)
            else:
                item_img_icon = get_icon_id('image_broken')
        split = row.split(percentage=0.08)
        split.label(str(index))
        split = split.split(percentage=0.797)
        split.prop(item, 'img_name', text='', emboss=False, icon_value=item_img_icon)
        split = split.split(align=True)
        if item.img_type == 1:
            split.prop(item, 'img_color', text='')
            split.operator('smc.img_reset', text='', icon_value=get_icon_id('clear')).list_id = index
        elif item.img_type == 2:
            split.prop(item, 'img_color', text='')
            split.operator('smc.img_reset', text='', icon_value=get_icon_id('clear')).list_id = index
        else:
            split.operator('smc.img_color', text='', icon_value=get_icon_id('diffuse')).list_id = index
            split.operator('smc.img_path', text='', icon_value=get_icon_id('image_search')).list_id = index

    def invoke(self, context, event):
        pass

    def filter_items(self, context, data, propname):
        col = getattr(data, propname)
        filter_name = self.filter_name.lower()
        flt_flags = [
            self.bitflag_filter_item if any(
                filter_name in filter_set for filter_set in (str(i), item.img_name.lower(), item.img_path.lower()))
            else 0 for i, item in enumerate(col, 1)]

        if self.use_filter_sort_alpha:
            flt_neworder = [x[1] for x in sorted(
                zip([x[0] for x in sorted(enumerate(col), key=lambda x: x[1].img_name)],
                    range(len(col))))]
        else:
            flt_neworder = []
        return flt_flags, flt_neworder
