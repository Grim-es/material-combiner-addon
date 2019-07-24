# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import os

import bpy
from bpy.app.handlers import persistent
from subprocess import call
from . icons import get_icon_id

try:
    from .addon_updater import Updater as updater
except Exception as e:
    print("ERROR INITIALIZING UPDATER")
    print(str(e))

    class Singleton_updater_none(object):
        def __init__(self):
            self.addon = None
            self.verbose = False
            self.invalidupdater = True
            self.error = None
            self.error_msg = None
            self.async_checking = None

        def clear_state(self):
            self.addon = None
            self.verbose = False
            self.invalidupdater = True
            self.error = None
            self.error_msg = None
            self.async_checking = None

        def run_update(self): pass

        def check_for_update(self): pass

    updater = Singleton_updater_none()
    updater.error = "Error initializing updater module"
    updater.error_msg = str(e)

updater.addon = "smc"


def make_annotations(cls):
    if not hasattr(bpy.app, "version") or bpy.app.version < (2, 80):
        return cls
    bl_props = {k: v for k, v in cls.__dict__.items() if isinstance(v, tuple)}
    if bl_props:
        if '__annotations__' not in cls.__dict__:
            setattr(cls, '__annotations__', {})
        annotations = cls.__dict__['__annotations__']
        for k, v in bl_props.items():
            annotations[k] = v
            delattr(cls, k)
    return cls


def layout_split(layout, factor=0.0, align=False):
    if not hasattr(bpy.app, "version") or bpy.app.version < (2, 80):
        return layout.split(percentage=factor, align=align)
    return layout.split(factor=factor, align=align)


def get_user_preferences(context=None):
    if not context:
        context = bpy.context
    prefs = None
    if hasattr(context, "user_preferences"):
        prefs = context.user_preferences.addons.get(__package__, None)
    elif hasattr(context, "preferences"):
        prefs = context.preferences.addons.get(__package__, None)
    if prefs:
        return prefs.preferences
    return None


class addon_updater_install_popup(bpy.types.Operator):
    bl_label = "Update Material Combiner"
    bl_idname = updater.addon+".updater_install_popup"
    bl_description = "Popup menu to check and display current updates available"
    bl_options = {'REGISTER', 'INTERNAL'}

    clean_install = bpy.props.BoolProperty(
        name="Clean install",
        description="If enabled, completely clear the addon's folder before installing new update, creating a fresh install",
        default=False,
        options={'HIDDEN'}
    )
    ignore_enum = bpy.props.EnumProperty(
        name="Process update",
        description="Decide to install, ignore, or defer new addon update",
        items=[
            ("install","Update Now","Install update now"),
            ("ignore","Ignore", "Ignore this update to prevent future popups"),
            ("defer","Defer","Defer choice till next blender session")
        ],
        options={'HIDDEN'}
    )

    def check (self, context):
        return True

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        if updater.invalidupdater is True:
            layout.label(text="Updater module error")
            return
        elif updater.update_ready is True:
            col = layout.column()
            col.scale_y = 0.7
            col.label(text="Update {} ready!".format(str(updater.update_version)),
                      icon="LOOP_FORWARDS")
            col.label(text="Choose 'Update Now' & press OK to install, ", icon="BLANK1")
            col.label(text="or click outside window to defer", icon="BLANK1")
            row = col.row()
            row.prop(self, "ignore_enum", expand=True)
            col.split()
        elif updater.update_ready is False:
            col = layout.column()
            col.scale_y = 0.7
            col.label(text="No updates available")
            col.label(text="Press okay to dismiss dialog")
        else:
            layout.label(text="Check for update now?")

    def execute(self, context):

        if updater.invalidupdater is True:
            return {'CANCELLED'}

        if updater.manual_only is True:
            bpy.ops.wm.url_open(url=updater.website)
        elif updater.update_ready is True:

            if self.ignore_enum == 'defer':
                return {'FINISHED'}
            elif self.ignore_enum == 'ignore':
                updater.ignore_update()
                return {'FINISHED'}

            res = updater.run_update(force=False,
                                     callback=post_update_callback,
                                     clean=self.clean_install)
            if updater.verbose:
                if res == 0:
                    print("Updater returned successful")
                else:
                    print("Updater returned {}, error occurred".format(res))
        elif updater.update_ready is None:
            _ = updater.check_for_update(now=True)

            atr = addon_updater_install_popup.bl_idname.split(".")
            getattr(getattr(bpy.ops, atr[0]), atr[1])('INVOKE_DEFAULT')
        else:
            if updater.verbose:
                print("Doing nothing, not ready for update")
        return {'FINISHED'}


class addon_updater_check_now(bpy.types.Operator):
    bl_label = "Check now for update"
    bl_idname = updater.addon+".updater_check_now"
    bl_description = "Check now for an update to the Material Combiner"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        if updater.invalidupdater is True:
            return {'CANCELLED'}

        if updater.async_checking is True and updater.error is None:
            return {'CANCELLED'}

        settings = get_user_preferences(context)
        if not settings:
            if updater.verbose:
                print("Could not get {} preferences, update check skipped".format(__package__))
            return {'CANCELLED'}
        updater.set_check_interval(enable=settings.auto_check_update,
                                   months=settings.updater_intrval_months,
                                   days=settings.updater_intrval_days,
                                   hours=settings.updater_intrval_hours,
                                   minutes=settings.updater_intrval_minutes)
        updater.check_for_update_now(ui_refresh)
        try:
            import pip
            call([bpy.app.binary_path_python, '-m', 'pip', 'install', 'pip', '--user', '--upgrade'], shell=True)
            call([bpy.app.binary_path_python, '-m', 'pip', 'install', 'Pillow', '--user', '--upgrade'], shell=True)
        except ImportError:
            call([bpy.app.binary_path_python, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'operators',
                                                           'get-pip.py'), '--user'], shell=True)
            call([bpy.app.binary_path_python, '-m', 'pip', 'install', 'Pillow', '--user', '--upgrade'], shell=True)
        return {'FINISHED'}


class addon_updater_update_now(bpy.types.Operator):
    bl_label = "Update "+updater.addon+" addon now"
    bl_idname = updater.addon+".updater_update_now"
    bl_description = "Update to the latest version of the Material Combiner"
    bl_options = {'REGISTER', 'INTERNAL'}

    clean_install = bpy.props.BoolProperty(
        name="Clean install",
        description="If enabled, completely clear the addon's folder before installing new update, creating a fresh install",
        default=False,
        options={'HIDDEN'}
    )

    def execute(self, context):

        if updater.invalidupdater == True:
            return {'CANCELLED'}

        if updater.manual_only == True:
            bpy.ops.wm.url_open(url=updater.website)
        if updater.update_ready == True:
            # if it fails, offer to open the website instead
            try:
                res = updater.run_update(force=False,
                                         callback=post_update_callback,
                                         clean=self.clean_install)

                if updater.verbose:
                    if res == 0:
                        print("Updater returned successful")
                    else:
                        print("Updater returned "+str(res)+", error occurred")
            except Exception as ex:
                updater._error = "Error trying to run update"
                updater._error_msg = str(ex)
                atr = addon_updater_install_manually.bl_idname.split(".")
                getattr(getattr(bpy.ops, atr[0]), atr[1])('INVOKE_DEFAULT')
        elif updater.update_ready is None:
            update_ready,  version,  link = updater.check_for_update(now=True)
            atr = addon_updater_install_popup.bl_idname.split(".")
            getattr(getattr(bpy.ops, atr[0]), atr[1])('INVOKE_DEFAULT')

        elif updater.update_ready is False:
            self.report({'INFO'}, "Nothing to update")
        else:
            self.report({'ERROR'}, "Encountered problem while trying to update")

        return {'FINISHED'}


class addon_updater_update_target(bpy.types.Operator):
    bl_label = updater.addon+" version target"
    bl_idname = updater.addon+".updater_update_target"
    bl_description = "Install a targeted version of the Material Combiner"
    bl_options = {'REGISTER', 'INTERNAL'}

    def target_version(self, context):
        if updater.invalidupdater is True:
            ret = []

        ret = []
        i = 0
        for tag in updater.tags:
            ret.append((tag, tag, "Select to install "+tag))
            i += 1
        return ret

    target = bpy.props.EnumProperty(
        name="Target version to install",
        description="Select the version to install",
        items=target_version
        )

    clean_install = bpy.props.BoolProperty(
        name="Clean install",
        description="If enabled, completely clear the addon's folder before installing new update, creating a fresh install",
        default=False,
        options={'HIDDEN'}
    )

    @classmethod
    def poll(cls, context):
        if updater.invalidupdater is True:
            return False
        return updater.update_ready is not None and len(updater.tags) > 0

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        if updater.invalidupdater is True:
            layout.label(text="Updater error")
            return
        split = layout_split(layout, factor=0.66)
        subcol = split.column()
        subcol.label(text="Select install version")
        subcol = split.column()
        subcol.prop(self, "target", text="")

    def execute(self, context):

        if updater.invalidupdater == True:
            return {'CANCELLED'}

        res = updater.run_update(force=False,
                                 revert_tag=self.target,
                                 callback=post_update_callback,
                                 clean=self.clean_install)

        if res == 0:
            if updater.verbose:
                print("Updater returned successful")
        else:
            if updater.verbose:
                print("Updater returned "+str(res)+", error occurred")
            return {'CANCELLED'}

        return {'FINISHED'}


class addon_updater_install_manually(bpy.types.Operator):
    bl_label = "Install update manually"
    bl_idname = updater.addon+".updater_install_manually"
    bl_description = "Proceed to manually install update"
    bl_options = {'REGISTER', 'INTERNAL'}

    error = bpy.props.StringProperty(
        name="Error Occurred",
        default="",
        options={'HIDDEN'}
        )

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self)

    def draw(self, context):
        layout = self.layout

        if updater.invalidupdater is True:
            layout.label(text="Updater error")
            return

        if self.error != "":
            col = layout.column()
            col.scale_y = 0.7
            col.label(text="There was an issue trying to auto-install", icon="ERROR")
            col.label(text="Press the download button below and install", icon="BLANK1")
            col.label(text="the zip file like a normal addon.", icon="BLANK1")
        else:
            col = layout.column()
            col.scale_y = 0.7
            col.label(text="Install the addon manually")
            col.label(text="Press the download button below and install")
            col.label(text="the zip file like a normal addon.")

        row = layout.row()

        if updater.update_link is not None:
            row.operator("wm.url_open",
                         text="Direct download").url=updater.update_link
        else:
            row.operator("wm.url_open",
                         text="(failed to retrieve direct download)")
            row.enabled = False

            if updater.website is not None:
                row = layout.row()
                row.operator("wm.url_open", text="Open website").url = updater.website
            else:
                row = layout.row()
                row.label(text="See source website to download the update")

    def execute(self, context):
        return {'FINISHED'}


class addon_updater_updated_successful(bpy.types.Operator):
    bl_label = "Installation Report"
    bl_idname = updater.addon+".updater_update_successful"
    bl_description = "Update installation response"
    bl_options = {'REGISTER', 'INTERNAL', 'UNDO'}

    error = bpy.props.StringProperty(
        name="Error Occurred",
        default="",
        options={'HIDDEN'}
        )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_popup(self, event)

    def draw(self, context):
        layout = self.layout

        if updater.invalidupdater is True:
            layout.label(text="Updater error")
            return

        saved = updater.json
        if self.error != "":
            col = layout.column()
            col.scale_y = 0.7
            col.label(text="Error occurred, did not install", icon="ERROR")
            if updater.error_msg:
                msg = updater.error_msg
            else:
                msg = self.error
            col.label(text=str(msg), icon="BLANK1")
            rw = col.row()
            rw.scale_y = 2
            rw.operator("wm.url_open",
                        text="Click for manual download.",
                        icon="BLANK1").url = updater.website

        elif updater.auto_reload_post_update is False:
            if "just_restored" in saved and saved["just_restored"] is True:
                col = layout.column()
                col.scale_y = 0.7
                col.label(text="Addon restored", icon="RECOVER_LAST")
                col.label(text="Restart blender to reload.", icon="BLANK1")
                updater.json_reset_restore()
            else:
                col = layout.column()
                col.scale_y = 0.7
                col.label(text="Addon successfully installed", icon="FILE_TICK")
                col.label(text="Restart blender to reload.", icon="BLANK1")

        else:
            if "just_restored" in saved and saved["just_restored"] is True:
                col = layout.column()
                col.scale_y = 0.7
                col.label(text="Addon restored", icon="RECOVER_LAST")
                col.label(text="Consider restarting blender to fully reload.", icon="BLANK1")
                updater.json_reset_restore()
            else:
                col = layout.column()
                col.scale_y = 0.7
                col.label(text="Addon successfully installed", icon="FILE_TICK")
                col.label(text="Consider restarting blender to fully reload.", icon="BLANK1")

    def execute(self, context):
        return {'FINISHED'}


class addon_updater_restore_backup(bpy.types.Operator):
    bl_label = "Restore backup"
    bl_idname = updater.addon+".updater_restore_backup"
    bl_description = "Restore addon from backup"
    bl_options = {'REGISTER', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        try:
            return os.path.isdir(os.path.join(updater.stage_path,"backup"))
        except:
            return False

    def execute(self, context):
        if updater.invalidupdater is True:
            return {'CANCELLED'}
        updater.restore_backup()
        return {'FINISHED'}


class addon_updater_ignore(bpy.types.Operator):
    bl_label = "Ignore update"
    bl_idname = updater.addon+".updater_ignore"
    bl_description = "Ignore update to prevent future popups"
    bl_options = {'REGISTER', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        if updater.invalidupdater is True:
            return False
        elif updater.update_ready is True:
            return True
        else:
            return False

    def execute(self, context):
        if updater.invalidupdater is True:
            return {'CANCELLED'}
        updater.ignore_update()
        self.report({"INFO"}, "Open addon preferences for updater options")
        return {'FINISHED'}


class addon_updater_end_background(bpy.types.Operator):
    bl_label = "End background check"
    bl_idname = updater.addon+".end_background_check"
    bl_description = "Stop checking for update in the background"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        # in case of error importing updater
        if updater.invalidupdater is True:
            return {'CANCELLED'}
        updater.stop_async_check_update()
        return {'FINISHED'}


ran_autocheck_install_popup = False
ran_update_sucess_popup = False

ran_background_check = False


@persistent
def updater_run_success_popup_handler(scene):
    global ran_update_sucess_popup
    ran_update_sucess_popup = True

    if updater.invalidupdater is True:
        return

    try:
        bpy.app.handlers.scene_update_post.remove(
                updater_run_success_popup_handler)
    except:
        pass

    atr = addon_updater_updated_successful.bl_idname.split(".")
    getattr(getattr(bpy.ops, atr[0]), atr[1])('INVOKE_DEFAULT')


@persistent
def updater_run_install_popup_handler(scene):
    global ran_autocheck_install_popup
    ran_autocheck_install_popup = True

    if updater.invalidupdater is True:
        return

    try:
        bpy.app.handlers.scene_update_post.remove(
                updater_run_install_popup_handler)
    except:
        pass

    if "ignore" in updater.json and updater.json["ignore"] is True:
        return
    elif "version_text" in updater.json and "version" in updater.json["version_text"]:
        version = updater.json["version_text"]["version"]
        ver_tuple = updater.version_tuple_from_text(version)

        if ver_tuple < updater.current_version:
            if updater.verbose:
                print("{} updater: appears user updated, clearing flag".format(updater.addon))
            updater.json_reset_restore()
            return
    atr = addon_updater_install_popup.bl_idname.split(".")
    getattr(getattr(bpy.ops, atr[0]), atr[1])('INVOKE_DEFAULT')


def background_update_callback(update_ready):
    global ran_autocheck_install_popup

    if updater.invalidupdater is True:
        return
    if updater.showpopups is False:
        return
    if update_ready is not True:
        return
    if updater_run_install_popup_handler not in bpy.app.handlers.scene_update_post and \
            ran_autocheck_install_popup is False:
        bpy.app.handlers.scene_update_post.append(updater_run_install_popup_handler)
        ran_autocheck_install_popup = True


def post_update_callback(module_name, res=None):
    if updater.invalidupdater is True:
        return

    if res is None:
        if updater.verbose:
            print("{} updater: Running post update callback".format(updater.addon))

        atr = addon_updater_updated_successful.bl_idname.split(".")
        getattr(getattr(bpy.ops, atr[0]),atr[1])('INVOKE_DEFAULT')
        global ran_update_sucess_popup
        ran_update_sucess_popup = True
    else:
        atr = addon_updater_updated_successful.bl_idname.split(".")
        getattr(getattr(bpy.ops, atr[0]), atr[1])('INVOKE_DEFAULT',error=res)
    return


def ui_refresh(update_status):
    for windowManager in bpy.data.window_managers:
        for window in windowManager.windows:
            for area in window.screen.areas:
                area.tag_redraw()


def check_for_update_background():
    if updater.invalidupdater is True:
        return
    global ran_background_check
    if ran_background_check is True:
        return
    elif updater.update_ready is not None or updater.async_checking is True:
        return

    settings = get_user_preferences(bpy.context)
    if not settings:
        return
    updater.set_check_interval(enable=settings.auto_check_update,
                               months=settings.updater_intrval_months,
                               days=settings.updater_intrval_days,
                               hours=settings.updater_intrval_hours,
                               minutes=settings.updater_intrval_minutes)

    if updater.verbose:
        print("{} updater: Running background check for update".format(updater.addon))
    updater.check_for_update_async(background_update_callback)
    ran_background_check = True


def check_for_update_nonthreaded(self, context):
    if updater.invalidupdater is True:
        return

    settings = get_user_preferences(bpy.context)
    if not settings:
        if updater.verbose:
            print("Could not get {} preferences, update check skipped".format(
                __package__))
        return
    updater.set_check_interval(enable=settings.auto_check_update,
                               months=settings.updater_intrval_months,
                               days=settings.updater_intrval_days,
                               hours=settings.updater_intrval_hours,
                               minutes=settings.updater_intrval_minutes)

    update_ready, version, link = updater.check_for_update(now=False)
    if update_ready is True:
        atr = addon_updater_install_popup.bl_idname.split(".")
        getattr(getattr(bpy.ops, atr[0]), atr[1])('INVOKE_DEFAULT')
    else:
        if updater.verbose: print("No update ready")
        self.report({'INFO'}, "No update ready")


def showReloadPopup():
    if updater.invalidupdater is True:
        return
    saved_state = updater.json
    global ran_update_sucess_popup

    a = saved_state is not None
    b = "just_updated" in saved_state
    c = saved_state["just_updated"]

    if a and b and c:
        updater.json_reset_postupdate()

        if updater.auto_reload_post_update is False:
            return

        if updater_run_success_popup_handler not in bpy.app.handlers.scene_update_post and \
                ran_update_sucess_popup is False:
            bpy.app.handlers.scene_update_post.append(updater_run_success_popup_handler)
            ran_update_sucess_popup = True


def update_notice_box_ui(self, context):

    if updater.invalidupdater is True:
        return

    saved_state = updater.json
    if updater.auto_reload_post_update is False:
        if "just_updated" in saved_state and saved_state["just_updated"] is True:
            layout = self.layout
            box = layout.box()
            col = box.column()
            col.scale_y = 0.7
            col.label(text="Restart blender", icon="ERROR")
            col.label(text="to complete update")
            return

    if "ignore" in updater.json and updater.json["ignore"] is True:
        return
    if updater.update_ready is not True:
        return

    layout = self.layout
    box = layout.box()
    col = box.column(align=True)
    col.label(text="Update ready!", icon="ERROR")
    col.separator()
    row = col.row(align=True)
    split = row.split(align=True)
    colL = split.column(align=True)
    colL.scale_y = 1.5
    colL.operator(addon_updater_ignore.bl_idname,icon="X",text="Ignore")
    colR = split.column(align=True)
    colR.scale_y = 1.5
    if updater.manual_only is False:
        colR.operator(addon_updater_update_now.bl_idname, text="Update", icon="LOOP_FORWARDS")
        col.operator("wm.url_open", text="Open website").url = updater.website
        col.operator(addon_updater_install_manually.bl_idname, text="Install manually")
    else:
        col.operator("wm.url_open", text="Get it now").url = updater.website


def update_settings_ui(self, context, element=None):
    if element is None:
        element = self.layout
    box = element.box()

    col = box.column(align=True)
    row = col.row(align=True)
    row.scale_y = 0.8
    row.label(text='Updates:', icon_value=get_icon_id('download'))

    if updater.invalidupdater is True:
        box.label(text="Error initializing updater code:")
        box.label(text=updater.error_msg)
        return

    settings = get_user_preferences(context)
    if not settings:
        box.label(text="Error getting updater preferences", icon='ERROR')
        return

    if updater.auto_reload_post_update is False:
        saved_state = updater.json
        if "just_updated" in saved_state and saved_state["just_updated"] == True:
            row.label(text="Restart blender to complete update", icon="ERROR")
            return

    row = box.row()
    col = row.column()
    if updater.error is not None:
        subcol = col.row(align=True)
        subcol.scale_y = 1
        split = subcol.split(align=True)
        split.scale_y = 2
        if "ssl" in updater.error_msg.lower():
            split.enabled = True
            split.operator(addon_updater_install_manually.bl_idname, text=updater.error)
        else:
            split.enabled = False
            split.operator(addon_updater_check_now.bl_idname, text=updater.error)
        split = subcol.split(align=True)
        split.scale_y = 2
        split.operator(addon_updater_check_now.bl_idname, text="", icon="FILE_REFRESH")

    elif updater.update_ready is None and updater.async_checking is False:
        col.scale_y = 2
        col.operator(addon_updater_check_now.bl_idname)
    elif updater.update_ready is None:
        subcol = col.row(align=True)
        subcol.scale_y = 1
        split = subcol.split(align=True)
        split.enabled = False
        split.scale_y = 2
        split.operator(addon_updater_check_now.bl_idname, text="Checking...")
        split = subcol.split(align=True)
        split.scale_y = 2
        split.operator(addon_updater_end_background.bl_idname, text="", icon="X")

    elif updater.include_branches is True and len(
            updater.tags) == len(updater.include_branch_list) and updater.manual_only is False:
        subcol = col.row(align=True)
        subcol.scale_y = 1
        split = subcol.split(align=True)
        split.scale_y = 2
        split.operator(addon_updater_update_now.bl_idname,
                       text="Update directly to " + str(updater.include_branch_list[0]))
        split = subcol.split(align=True)
        split.scale_y = 2
        split.operator(addon_updater_check_now.bl_idname, text="", icon="FILE_REFRESH")

    elif updater.update_ready is True and updater.manual_only is False:
        subcol = col.row(align=True)
        subcol.scale_y = 1
        split = subcol.split(align=True)
        split.scale_y = 2
        split.operator(addon_updater_update_now.bl_idname, text="Update now to " + str(updater.update_version))
        split = subcol.split(align=True)
        split.scale_y = 2
        split.operator(addon_updater_check_now.bl_idname, text="", icon="FILE_REFRESH")

    elif updater.update_ready is True and updater.manual_only is True:
        col.scale_y = 2
        col.operator("wm.url_open", text="Download "+str(updater.update_version)).url = updater.website
    else:
        subcol = col.row(align=True)
        subcol.scale_y = 1
        split = subcol.split(align=True)
        split.enabled = False
        split.scale_y = 2
        split.operator(addon_updater_check_now.bl_idname, text="Addon is up to date")
        split = subcol.split(align=True)
        split.scale_y = 2
        split.operator(addon_updater_check_now.bl_idname, text="", icon="FILE_REFRESH")

    if updater.manual_only is False:
        col = row.column(align=True)
        if updater.include_branches is True and len(updater.include_branch_list) > 0:
            branch = updater.include_branch_list[0]
            col.operator(addon_updater_update_target.bl_idname,
                         text="Install latest {} / old version".format(branch))
        else:
            col.operator(addon_updater_update_target.bl_idname,
                         text="Reinstall / install old version")
        lastdate = "none found"
        backuppath = os.path.join(updater.stage_path,"backup")
        if "backup_date" in updater.json and os.path.isdir(backuppath):
            if updater.json["backup_date"] == "":
                lastdate = "Date not found"
            else:
                lastdate = updater.json["backup_date"]
        backuptext = "Restore addon backup ({})".format(lastdate)
        col.operator(addon_updater_restore_backup.bl_idname, text=backuptext)

    row = box.row()
    row.scale_y = 0.7
    lastcheck = updater.json["last_check"]
    if updater.error is not None and updater.error_msg is not None:
        row.label(text=updater.error_msg)
    elif lastcheck != "" and lastcheck is not None:
        lastcheck = lastcheck[0: lastcheck.index(".")]
        row.label(text="Last update check: " + lastcheck)
    else:
        row.label(text="Last update check: Never")


def update_settings_ui_condensed(self, context, element=None):
    if element is None:
        element = self.layout
    row = element.row()

    if updater.invalidupdater is True:
        row.label(text="Error initializing updater code:")
        row.label(text=updater.error_msg)
        return

    settings = get_user_preferences(context)

    if not settings:
        row.label(text="Error getting updater preferences", icon='ERROR')
        return

    if updater.auto_reload_post_update is False:
        saved_state = updater.json
        if "just_updated" in saved_state and saved_state["just_updated"] is True:
            row.label(text="Restart blender to complete update", icon="ERROR")
            return

    col = row.column()
    if updater.error is not None:
        subcol = col.row(align=True)
        subcol.scale_y = 1
        split = subcol.split(align=True)
        split.scale_y = 2
        if "ssl" in updater.error_msg.lower():
            split.enabled = True
            split.operator(addon_updater_install_manually.bl_idname, text=updater.error)
        else:
            split.enabled = False
            split.operator(addon_updater_check_now.bl_idname, text=updater.error)
        split = subcol.split(align=True)
        split.scale_y = 2
        split.operator(addon_updater_check_now.bl_idname, text="", icon="FILE_REFRESH")

    elif updater.update_ready is None and updater.async_checking is False:
        col.scale_y = 2
        col.operator(addon_updater_check_now.bl_idname)
    elif updater.update_ready is None:
        subcol = col.row(align=True)
        subcol.scale_y = 1
        split = subcol.split(align=True)
        split.enabled = False
        split.scale_y = 2
        split.operator(addon_updater_check_now.bl_idname, text="Checking...")
        split = subcol.split(align=True)
        split.scale_y = 2
        split.operator(addon_updater_end_background.bl_idname, text="", icon="X")

    elif updater.include_branches is True and len(
            updater.tags) == len(updater.include_branch_list) and updater.manual_only==False:
        subcol = col.row(align=True)
        subcol.scale_y = 1
        split = subcol.split(align=True)
        split.scale_y = 2
        split.operator(addon_updater_update_now.bl_idname,
                       text="Update directly to " + str(updater.include_branch_list[0]))
        split = subcol.split(align=True)
        split.scale_y = 2
        split.operator(addon_updater_check_now.bl_idname, text="", icon="FILE_REFRESH")

    elif updater.update_ready is True and updater.manual_only is False:
        subcol = col.row(align=True)
        subcol.scale_y = 1
        split = subcol.split(align=True)
        split.scale_y = 2
        split.operator(addon_updater_update_now.bl_idname,
                       text="Update now to " + str(updater.update_version))
        split = subcol.split(align=True)
        split.scale_y = 2
        split.operator(addon_updater_check_now.bl_idname, text="", icon="FILE_REFRESH")

    elif updater.update_ready is True and updater.manual_only is True:
        col.scale_y = 2
        col.operator("wm.url_open", text="Download "+str(updater.update_version)).url=updater.website
    else:
        subcol = col.row(align=True)
        subcol.scale_y = 1
        split = subcol.split(align=True)
        split.enabled = False
        split.scale_y = 2
        split.operator(addon_updater_check_now.bl_idname, text="Addon is up to date")
        split = subcol.split(align=True)
        split.scale_y = 2
        split.operator(addon_updater_check_now.bl_idname, text="", icon="FILE_REFRESH")

    row = element.row()
    row.prop(settings, "auto_check_update")

    row = element.row()
    row.scale_y = 0.7
    lastcheck = updater.json["last_check"]
    if updater.error is not None and updater.error_msg is not None:
        row.label(text=updater.error_msg)
    elif lastcheck != "" and lastcheck is not None:
        lastcheck = lastcheck[0: lastcheck.index(".")]
        row.label(text="Last check: " + lastcheck)
    else:
        row.label(text="Last check: Never")


def skip_tag_function(self, tag):
    if self.invalidupdater is True:
        return False

    if self.include_branches is True:
        for branch in self.include_branch_list:
            if tag["name"].lower() == branch:
                return False

    tupled = self.version_tuple_from_text(tag["name"])
    if type(tupled) != type((1, 2, 3)):
        return True

    if self.version_min_update is not None:
        if tupled < self.version_min_update:
            return True

    if self.version_max_update is not None:
        if tupled >= self.version_max_update:
            return True

    return False


def select_link_function(self, tag):
    link = tag["zipball_url"]
    return link


classes = (
    addon_updater_install_popup,
    addon_updater_check_now,
    addon_updater_update_now,
    addon_updater_update_target,
    addon_updater_install_manually,
    addon_updater_updated_successful,
    addon_updater_restore_backup,
    addon_updater_ignore,
    addon_updater_end_background
)


def register(bl_info):
    if updater.error:
        print("Exiting updater registration, " + updater.error)
        return
    updater.clear_state()
    updater.engine = "Github"
    updater.private_token = None
    updater.user = "Grim-es"
    updater.repo = "material-combiner-addon"
    updater.website = "https://github.com/Grim-es/material-combiner-addon/archive/v2_beta.zip"
    updater.subfolder_path = ""
    updater.current_version = bl_info["version"]
    updater.verbose = False
    updater.backup_current = False
    updater.backup_ignore_patterns = ["*"]
    updater.overwrite_patterns = ["*"]
    updater.remove_pre_update_patterns = ["*"]
    updater.include_branches = False
    updater.use_releases = False
    updater.include_branch_list = None
    updater.manual_only = False
    updater.fake_install = False
    updater.showpopups = True
    updater.version_min_update = (1, 1, 6, 4)
    updater.version_max_update = None
    updater.skip_tag = skip_tag_function
    updater.select_link = select_link_function

    for cls in classes:
        make_annotations(cls)
        bpy.utils.register_class(cls)

    showReloadPopup()


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    updater.clear_state()

    global ran_autocheck_install_popup
    ran_autocheck_install_popup = False

    global ran_update_sucess_popup
    ran_update_sucess_popup = False

    global ran_background_check
    ran_background_check = False
