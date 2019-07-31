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
from subprocess import call

import bpy
from bpy.app.handlers import persistent
from .icons import get_icon_id

try:
    from .addon_updater import Updater
except Exception as e:
    print("ERROR INITIALIZING UPDATER")
    print(str(e))


    class SingletonUpdaterNone(object):
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


    Updater = SingletonUpdaterNone()
    Updater.error = "Error initializing updater module"
    Updater.error_msg = str(e)

Updater.addon = "smc"


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


class AddonUpdaterInstallPopup(bpy.types.Operator):
    bl_label = "Update Material Combiner"
    bl_idname = Updater.addon + ".updater_install_popup"
    bl_description = "Popup menu to check and display current updates available"
    bl_options = {'REGISTER', 'INTERNAL'}

    clean_install = bpy.props.BoolProperty(
        name="Clean install",
        description="If enabled, completely clear the addon's folder before"
                    "installing new update, creating a fresh install",
        default=False,
        options={'HIDDEN'}
    )
    ignore_enum = bpy.props.EnumProperty(
        name="Process update",
        description="Decide to install, ignore, or defer new addon update",
        items=[
            ("install", "Update Now", "Install update now"),
            ("ignore", "Ignore", "Ignore this update to prevent future popups"),
            ("defer", "Defer", "Defer choice till next blender session")
        ],
        options={'HIDDEN'}
    )

    def check(self, context):
        return True

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        if Updater.invalidupdater is True:
            layout.label(text="Updater module error")
            return
        elif Updater.update_ready is True:
            col = layout.column()
            col.scale_y = 0.7
            col.label(text="Update {} ready!".format(str(Updater.update_version)),
                      icon="LOOP_FORWARDS")
            col.label(text="Choose 'Update Now' & press OK to install, ", icon="BLANK1")
            col.label(text="or click outside window to defer", icon="BLANK1")
            row = col.row()
            row.prop(self, "ignore_enum", expand=True)
            col.split()
        elif Updater.update_ready is False:
            col = layout.column()
            col.scale_y = 0.7
            col.label(text="No updates available")
            col.label(text="Press okay to dismiss dialog")
        else:
            layout.label(text="Check for update now?")

    def execute(self, context):

        if Updater.invalidupdater is True:
            return {'CANCELLED'}

        if Updater.manual_only is True:
            bpy.ops.wm.url_open(url=Updater.website)
        elif Updater.update_ready is True:

            if self.ignore_enum == 'defer':
                return {'FINISHED'}
            elif self.ignore_enum == 'ignore':
                Updater.ignore_update()
                return {'FINISHED'}

            res = Updater.run_update(force=False,
                                     callback=post_update_callback,
                                     clean=self.clean_install)
            if Updater.verbose:
                if res == 0:
                    print("Updater returned successful")
                else:
                    print("Updater returned {}, error occurred".format(res))
        elif Updater.update_ready is None:
            _ = Updater.check_for_update(now=True)

            atr = AddonUpdaterInstallPopup.bl_idname.split(".")
            getattr(getattr(bpy.ops, atr[0]), atr[1])('INVOKE_DEFAULT')
        else:
            if Updater.verbose:
                print("Doing nothing, not ready for update")
        return {'FINISHED'}


class AddonUpdaterCheckNow(bpy.types.Operator):
    bl_label = "Check now for update"
    bl_idname = Updater.addon + ".updater_check_now"
    bl_description = "Check now for an update to the Material Combiner"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        if Updater.invalidupdater is True:
            return {'CANCELLED'}

        if Updater.async_checking is True and Updater.error is None:
            return {'CANCELLED'}

        settings = get_user_preferences(context)
        if not settings:
            if Updater.verbose:
                print("Could not get {} preferences, update check skipped".format(__package__))
            return {'CANCELLED'}
        Updater.set_check_interval(enable=settings.auto_check_update,
                                   months=settings.updater_intrval_months,
                                   days=settings.updater_intrval_days,
                                   hours=settings.updater_intrval_hours,
                                   minutes=settings.updater_intrval_minutes)
        Updater.check_for_update_now(ui_refresh)
        try:
            import pip
            call([bpy.app.binary_path_python, '-m', 'pip', 'install', 'pip', '--user', '--upgrade'], shell=True)
            call([bpy.app.binary_path_python, '-m', 'pip', 'install', 'Pillow', '--user', '--upgrade'], shell=True)
        except ImportError:
            call([bpy.app.binary_path_python, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'operators',
                                                           'get-pip.py'), '--user'], shell=True)
            call([bpy.app.binary_path_python, '-m', 'pip', 'install', 'Pillow', '--user', '--upgrade'], shell=True)
        return {'FINISHED'}


class AddonUpdaterUpdateNow(bpy.types.Operator):
    bl_label = "Update " + Updater.addon + " addon now"
    bl_idname = Updater.addon + ".updater_update_now"
    bl_description = "Update to the latest version of the Material Combiner"
    bl_options = {'REGISTER', 'INTERNAL'}

    clean_install = bpy.props.BoolProperty(
        name="Clean install",
        description="If enabled, completely clear the addon's folder before"
                    "installing new update, creating a fresh install",
        default=False,
        options={'HIDDEN'}
    )

    def execute(self, context):

        if Updater.invalidupdater is True:
            return {'CANCELLED'}

        if Updater.manual_only is True:
            bpy.ops.wm.url_open(url=Updater.website)
        if Updater.update_ready is True:
            # if it fails, offer to open the website instead
            try:
                res = Updater.run_update(force=False,
                                         callback=post_update_callback,
                                         clean=self.clean_install)

                if Updater.verbose:
                    if res == 0:
                        print("Updater returned successful")
                    else:
                        print("Updater returned " + str(res) + ", error occurred")
            except Exception as ex:
                Updater._error = "Error trying to run update"
                Updater._error_msg = str(ex)
                atr = AddonUpdaterInstallManually.bl_idname.split(".")
                getattr(getattr(bpy.ops, atr[0]), atr[1])('INVOKE_DEFAULT')
        elif Updater.update_ready is None:
            update_ready, version, link = Updater.check_for_update(now=True)
            atr = AddonUpdaterInstallPopup.bl_idname.split(".")
            getattr(getattr(bpy.ops, atr[0]), atr[1])('INVOKE_DEFAULT')

        elif Updater.update_ready is False:
            self.report({'INFO'}, "Nothing to update")
        else:
            self.report({'ERROR'}, "Encountered problem while trying to update")

        return {'FINISHED'}


class AddonUpdaterUpdateTarget(bpy.types.Operator):
    bl_label = Updater.addon + " version target"
    bl_idname = Updater.addon + ".updater_update_target"
    bl_description = "Install a targeted version of the Material Combiner"
    bl_options = {'REGISTER', 'INTERNAL'}

    def target_version(self, _):
        ret = []
        i = 0
        for tag in Updater.tags:
            ret.append((tag, tag, "Select to install " + tag))
            i += 1
        return ret

    target = bpy.props.EnumProperty(
        name="Target version to install",
        description="Select the version to install",
        items=target_version
    )

    clean_install = bpy.props.BoolProperty(
        name="Clean install",
        description="If enabled, completely clear the addon's folder before"
                    "installing new update, creating a fresh install",
        default=False,
        options={'HIDDEN'}
    )

    @classmethod
    def poll(cls, _):
        if Updater.invalidupdater is True:
            return False
        return Updater.update_ready is not None and len(Updater.tags) > 0

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        if Updater.invalidupdater is True:
            layout.label(text="Updater error")
            return
        split = layout_split(layout, factor=0.66)
        subcol = split.column()
        subcol.label(text="Select install version")
        subcol = split.column()
        subcol.prop(self, "target", text="")

    def execute(self, context):

        if Updater.invalidupdater is True:
            return {'CANCELLED'}

        res = Updater.run_update(force=False,
                                 revert_tag=self.target,
                                 callback=post_update_callback,
                                 clean=self.clean_install)

        if res == 0:
            if Updater.verbose:
                print("Updater returned successful")
        else:
            if Updater.verbose:
                print("Updater returned " + str(res) + ", error occurred")
            return {'CANCELLED'}

        return {'FINISHED'}


class AddonUpdaterInstallManually(bpy.types.Operator):
    bl_label = "Install update manually"
    bl_idname = Updater.addon + ".updater_install_manually"
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

        if Updater.invalidupdater is True:
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

        if Updater.update_link is not None:
            row.operator("wm.url_open",
                         text="Direct download").url = Updater.update_link
        else:
            row.operator("wm.url_open",
                         text="(failed to retrieve direct download)")
            row.enabled = False

            if Updater.website is not None:
                row = layout.row()
                row.operator("wm.url_open", text="Open website").url = Updater.website
            else:
                row = layout.row()
                row.label(text="See source website to download the update")

    def execute(self, context):
        return {'FINISHED'}


class AddonUpdaterUpdatedSuccessful(bpy.types.Operator):
    bl_label = "Installation Report"
    bl_idname = Updater.addon + ".updater_update_successful"
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

        if Updater.invalidupdater is True:
            layout.label(text="Updater error")
            return

        saved = Updater.json
        if self.error != "":
            col = layout.column()
            col.scale_y = 0.7
            col.label(text="Error occurred, did not install", icon="ERROR")
            if Updater.error_msg:
                msg = Updater.error_msg
            else:
                msg = self.error
            col.label(text=str(msg), icon="BLANK1")
            rw = col.row()
            rw.scale_y = 2
            rw.operator("wm.url_open",
                        text="Click for manual download.",
                        icon="BLANK1").url = Updater.website

        elif Updater.auto_reload_post_update is False:
            if "just_restored" in saved and saved["just_restored"] is True:
                col = layout.column()
                col.scale_y = 0.7
                col.label(text="Addon restored", icon="RECOVER_LAST")
                col.label(text="Restart blender to reload.", icon="BLANK1")
                Updater.json_reset_restore()
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
                Updater.json_reset_restore()
            else:
                col = layout.column()
                col.scale_y = 0.7
                col.label(text="Addon successfully installed", icon="FILE_TICK")
                col.label(text="Consider restarting blender to fully reload.", icon="BLANK1")

    def execute(self, context):
        return {'FINISHED'}


class AddonUpdaterRestoreBackup(bpy.types.Operator):
    bl_label = "Restore backup"
    bl_idname = Updater.addon + ".updater_restore_backup"
    bl_description = "Restore addon from backup"
    bl_options = {'REGISTER', 'INTERNAL'}

    @classmethod
    def poll(cls, _):
        try:
            return os.path.isdir(os.path.join(Updater.stage_path, "backup"))
        except OSError:
            return False

    def execute(self, context):
        if Updater.invalidupdater is True:
            return {'CANCELLED'}
        Updater.restore_backup()
        return {'FINISHED'}


class AddonUpdaterIgnore(bpy.types.Operator):
    bl_label = "Ignore update"
    bl_idname = Updater.addon + ".updater_ignore"
    bl_description = "Ignore update to prevent future popups"
    bl_options = {'REGISTER', 'INTERNAL'}

    @classmethod
    def poll(cls, _):
        if Updater.invalidupdater is True:
            return False
        elif Updater.update_ready is True:
            return True
        else:
            return False

    def execute(self, context):
        if Updater.invalidupdater is True:
            return {'CANCELLED'}
        Updater.ignore_update()
        self.report({"INFO"}, "Open addon preferences for updater options")
        return {'FINISHED'}


class AddonUpdaterEndBackground(bpy.types.Operator):
    bl_label = "End background check"
    bl_idname = Updater.addon + ".end_background_check"
    bl_description = "Stop checking for update in the background"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        # in case of error importing updater
        if Updater.invalidupdater is True:
            return {'CANCELLED'}
        Updater.stop_async_check_update()
        return {'FINISHED'}


ran_autocheck_install_popup = False
ran_update_sucess_popup = False

ran_background_check = False


@persistent
def updater_run_success_popup_handler(_):
    global ran_update_sucess_popup
    ran_update_sucess_popup = True

    if Updater.invalidupdater is True:
        return

    try:
        if hasattr(bpy.app.handlers, 'depsgraph_update_post'):
            bpy.app.handlers.depsgraph_update_post.remove(
                updater_run_success_popup_handler)
        else:
            bpy.app.handlers.scene_update_post.remove(
                updater_run_success_popup_handler)
    except ValueError:
        pass

    atr = AddonUpdaterUpdatedSuccessful.bl_idname.split(".")
    getattr(getattr(bpy.ops, atr[0]), atr[1])('INVOKE_DEFAULT')


@persistent
def updater_run_install_popup_handler(_):
    global ran_autocheck_install_popup
    ran_autocheck_install_popup = True

    if Updater.invalidupdater is True:
        return

    try:
        if hasattr(bpy.app.handlers, 'depsgraph_update_post'):
            bpy.app.handlers.depsgraph_update_post.remove(
                updater_run_install_popup_handler)
        else:
            bpy.app.handlers.scene_update_post.remove(
                updater_run_install_popup_handler)
    except ValueError:
        pass

    if "ignore" in Updater.json and Updater.json["ignore"] is True:
        return
    elif "version_text" in Updater.json and "version" in Updater.json["version_text"]:
        version = Updater.json["version_text"]["version"]
        ver_tuple = Updater.version_tuple_from_text(version)

        if ver_tuple < Updater.current_version:
            if Updater.verbose:
                print("{} updater: appears user updated, clearing flag".format(Updater.addon))
            Updater.json_reset_restore()
            return
    atr = AddonUpdaterInstallPopup.bl_idname.split(".")
    getattr(getattr(bpy.ops, atr[0]), atr[1])('INVOKE_DEFAULT')


def background_update_callback(update_ready):
    global ran_autocheck_install_popup

    if Updater.invalidupdater is True:
        return
    if Updater.showpopups is False:
        return
    if update_ready is not True:
        return
    if hasattr(bpy.app.handlers, 'depsgraph_update_post') and updater_run_install_popup_handler not in \
            bpy.app.handlers.depsgraph_update_post and ran_autocheck_install_popup is False:
        bpy.app.handlers.depsgraph_update_post.append(updater_run_install_popup_handler)
        ran_autocheck_install_popup = True
    elif updater_run_install_popup_handler not in bpy.app.handlers.scene_update_post and \
            ran_autocheck_install_popup is False:
        bpy.app.handlers.scene_update_post.append(updater_run_install_popup_handler)
        ran_autocheck_install_popup = True


def post_update_callback(_, res=None):
    if Updater.invalidupdater is True:
        return

    if res is None:
        if Updater.verbose:
            print("{} updater: Running post update callback".format(Updater.addon))

        atr = AddonUpdaterUpdatedSuccessful.bl_idname.split(".")
        getattr(getattr(bpy.ops, atr[0]), atr[1])('INVOKE_DEFAULT')
        global ran_update_sucess_popup
        ran_update_sucess_popup = True
    else:
        atr = AddonUpdaterUpdatedSuccessful.bl_idname.split(".")
        getattr(getattr(bpy.ops, atr[0]), atr[1])('INVOKE_DEFAULT', error=res)
    return


def ui_refresh(_):
    for windowManager in bpy.data.window_managers:
        for window in windowManager.windows:
            for area in window.screen.areas:
                area.tag_redraw()


def check_for_update_background():
    if Updater.invalidupdater is True:
        return
    global ran_background_check
    if ran_background_check is True:
        return
    elif Updater.update_ready is not None or Updater.async_checking is True:
        return

    settings = get_user_preferences(bpy.context)
    if not settings:
        return
    Updater.set_check_interval(enable=settings.auto_check_update,
                               months=settings.updater_intrval_months,
                               days=settings.updater_intrval_days,
                               hours=settings.updater_intrval_hours,
                               minutes=settings.updater_intrval_minutes)

    if Updater.verbose:
        print("{} updater: Running background check for update".format(Updater.addon))
    Updater.check_for_update_async(background_update_callback)
    ran_background_check = True


def check_for_update_nonthreaded(self, _):
    if Updater.invalidupdater is True:
        return

    settings = get_user_preferences(bpy.context)
    if not settings:
        if Updater.verbose:
            print("Could not get {} preferences, update check skipped".format(
                __package__))
        return
    Updater.set_check_interval(enable=settings.auto_check_update,
                               months=settings.updater_intrval_months,
                               days=settings.updater_intrval_days,
                               hours=settings.updater_intrval_hours,
                               minutes=settings.updater_intrval_minutes)

    update_ready, version, link = Updater.check_for_update(now=False)
    if update_ready is True:
        atr = AddonUpdaterInstallPopup.bl_idname.split(".")
        getattr(getattr(bpy.ops, atr[0]), atr[1])('INVOKE_DEFAULT')
    else:
        if Updater.verbose:
            print("No update ready")
        self.report({'INFO'}, "No update ready")


def show_reload_popup():
    if Updater.invalidupdater is True:
        return
    saved_state = Updater.json
    global ran_update_sucess_popup

    a = saved_state is not None
    b = "just_updated" in saved_state
    c = saved_state["just_updated"]

    if a and b and c:
        Updater.json_reset_postupdate()

        if Updater.auto_reload_post_update is False:
            return

        if hasattr(bpy.app.handlers, 'depsgraph_update_post') and updater_run_success_popup_handler not in \
                bpy.app.handlers.depsgraph_update_post and ran_update_sucess_popup is False:
            bpy.app.handlers.depsgraph_update_post.append(updater_run_success_popup_handler)
            ran_update_sucess_popup = True
        elif updater_run_success_popup_handler not in bpy.app.handlers.scene_update_post and \
                ran_update_sucess_popup is False:
            bpy.app.handlers.scene_update_post.append(updater_run_success_popup_handler)
            ran_update_sucess_popup = True


def update_notice_box_ui(self, _):
    if Updater.invalidupdater is True:
        return

    saved_state = Updater.json
    if Updater.auto_reload_post_update is False:
        if "just_updated" in saved_state and saved_state["just_updated"] is True:
            layout = self.layout
            box = layout.box()
            col = box.column()
            col.scale_y = 0.7
            col.label(text="Restart blender", icon="ERROR")
            col.label(text="to complete update")
            return

    if "ignore" in Updater.json and Updater.json["ignore"] is True:
        return
    if Updater.update_ready is not True:
        return

    layout = self.layout
    box = layout.box()
    col = box.column(align=True)
    col.label(text="Update ready!", icon="ERROR")
    col.separator()
    row = col.row(align=True)
    split = row.split(align=True)
    col_l = split.column(align=True)
    col_l.scale_y = 1.5
    col_l.operator(AddonUpdaterIgnore.bl_idname, icon="X", text="Ignore")
    col_r = split.column(align=True)
    col_r.scale_y = 1.5
    if Updater.manual_only is False:
        col_r.operator(AddonUpdaterUpdateNow.bl_idname, text="Update", icon="LOOP_FORWARDS")
        col.operator("wm.url_open", text="Open website").url = Updater.website
        col.operator(AddonUpdaterInstallManually.bl_idname, text="Install manually")
    else:
        col.operator("wm.url_open", text="Get it now").url = Updater.website


def update_settings_ui(self, context, element=None):
    if element is None:
        element = self.layout
    box = element.box()

    col = box.column(align=True)
    row = col.row(align=True)
    row.scale_y = 0.8
    row.label(text='Updates:', icon_value=get_icon_id('download'))

    if Updater.invalidupdater is True:
        box.label(text="Error initializing updater code:")
        box.label(text=Updater.error_msg)
        return

    settings = get_user_preferences(context)
    if not settings:
        box.label(text="Error getting updater preferences", icon='ERROR')
        return

    if Updater.auto_reload_post_update is False:
        saved_state = Updater.json
        if "just_updated" in saved_state and saved_state["just_updated"] is True:
            row.label(text="Restart blender to complete update", icon="ERROR")
            return

    row = box.row()
    col = row.column()
    if Updater.error is not None:
        subcol = col.row(align=True)
        subcol.scale_y = 1
        split = subcol.split(align=True)
        split.scale_y = 2
        if "ssl" in Updater.error_msg.lower():
            split.enabled = True
            split.operator(AddonUpdaterInstallManually.bl_idname, text=Updater.error)
        else:
            split.enabled = False
            split.operator(AddonUpdaterCheckNow.bl_idname, text=Updater.error)
        split = subcol.split(align=True)
        split.scale_y = 2
        split.operator(AddonUpdaterCheckNow.bl_idname, text="", icon="FILE_REFRESH")

    elif Updater.update_ready is None and Updater.async_checking is False:
        col.scale_y = 2
        col.operator(AddonUpdaterCheckNow.bl_idname)
    elif Updater.update_ready is None:
        subcol = col.row(align=True)
        subcol.scale_y = 1
        split = subcol.split(align=True)
        split.enabled = False
        split.scale_y = 2
        split.operator(AddonUpdaterCheckNow.bl_idname, text="Checking...")
        split = subcol.split(align=True)
        split.scale_y = 2
        split.operator(AddonUpdaterEndBackground.bl_idname, text="", icon="X")

    elif Updater.include_branches is True and len(
            Updater.tags) == len(Updater.include_branch_list) and Updater.manual_only is False:
        subcol = col.row(align=True)
        subcol.scale_y = 1
        split = subcol.split(align=True)
        split.scale_y = 2
        split.operator(AddonUpdaterUpdateNow.bl_idname,
                       text="Update directly to " + str(Updater.include_branch_list[0]))
        split = subcol.split(align=True)
        split.scale_y = 2
        split.operator(AddonUpdaterCheckNow.bl_idname, text="", icon="FILE_REFRESH")

    elif Updater.update_ready is True and Updater.manual_only is False:
        subcol = col.row(align=True)
        subcol.scale_y = 1
        split = subcol.split(align=True)
        split.scale_y = 2
        split.operator(AddonUpdaterUpdateNow.bl_idname, text="Update now to " + str(Updater.update_version))
        split = subcol.split(align=True)
        split.scale_y = 2
        split.operator(AddonUpdaterCheckNow.bl_idname, text="", icon="FILE_REFRESH")

    elif Updater.update_ready is True and Updater.manual_only is True:
        col.scale_y = 2
        col.operator("wm.url_open", text="Download " + str(Updater.update_version)).url = Updater.website
    else:
        subcol = col.row(align=True)
        subcol.scale_y = 1
        split = subcol.split(align=True)
        split.enabled = False
        split.scale_y = 2
        split.operator(AddonUpdaterCheckNow.bl_idname, text="Addon is up to date")
        split = subcol.split(align=True)
        split.scale_y = 2
        split.operator(AddonUpdaterCheckNow.bl_idname, text="", icon="FILE_REFRESH")

    if Updater.manual_only is False:
        col = row.column(align=True)
        if Updater.include_branches is True and len(Updater.include_branch_list) > 0:
            branch = Updater.include_branch_list[0]
            col.operator(AddonUpdaterUpdateTarget.bl_idname,
                         text="Install latest {} / old version".format(branch))
        else:
            col.operator(AddonUpdaterUpdateTarget.bl_idname,
                         text="Reinstall / install old version")
        lastdate = "none found"
        backuppath = os.path.join(Updater.stage_path, "backup")
        if "backup_date" in Updater.json and os.path.isdir(backuppath):
            if Updater.json["backup_date"] == "":
                lastdate = "Date not found"
            else:
                lastdate = Updater.json["backup_date"]
        backuptext = "Restore addon backup ({})".format(lastdate)
        col.operator(AddonUpdaterRestoreBackup.bl_idname, text=backuptext)

    row = box.row()
    row.scale_y = 0.7
    lastcheck = Updater.json["last_check"]
    if Updater.error is not None and Updater.error_msg is not None:
        row.label(text=Updater.error_msg)
    elif lastcheck != "" and lastcheck is not None:
        lastcheck = lastcheck[0: lastcheck.index(".")]
        row.label(text="Last update check: " + lastcheck)
    else:
        row.label(text="Last update check: Never")


def update_settings_ui_condensed(self, context, element=None):
    if element is None:
        element = self.layout
    row = element.row()

    if Updater.invalidupdater is True:
        row.label(text="Error initializing updater code:")
        row.label(text=Updater.error_msg)
        return

    settings = get_user_preferences(context)

    if not settings:
        row.label(text="Error getting updater preferences", icon='ERROR')
        return

    if Updater.auto_reload_post_update is False:
        saved_state = Updater.json
        if "just_updated" in saved_state and saved_state["just_updated"] is True:
            row.label(text="Restart blender to complete update", icon="ERROR")
            return

    col = row.column()
    if Updater.error is not None:
        subcol = col.row(align=True)
        subcol.scale_y = 1
        split = subcol.split(align=True)
        split.scale_y = 2
        if "ssl" in Updater.error_msg.lower():
            split.enabled = True
            split.operator(AddonUpdaterInstallManually.bl_idname, text=Updater.error)
        else:
            split.enabled = False
            split.operator(AddonUpdaterCheckNow.bl_idname, text=Updater.error)
        split = subcol.split(align=True)
        split.scale_y = 2
        split.operator(AddonUpdaterCheckNow.bl_idname, text="", icon="FILE_REFRESH")

    elif Updater.update_ready is None and Updater.async_checking is False:
        col.scale_y = 2
        col.operator(AddonUpdaterCheckNow.bl_idname)
    elif Updater.update_ready is None:
        subcol = col.row(align=True)
        subcol.scale_y = 1
        split = subcol.split(align=True)
        split.enabled = False
        split.scale_y = 2
        split.operator(AddonUpdaterCheckNow.bl_idname, text="Checking...")
        split = subcol.split(align=True)
        split.scale_y = 2
        split.operator(AddonUpdaterEndBackground.bl_idname, text="", icon="X")

    elif Updater.include_branches is True and len(
            Updater.tags) == len(Updater.include_branch_list) and Updater.manual_only is False:
        subcol = col.row(align=True)
        subcol.scale_y = 1
        split = subcol.split(align=True)
        split.scale_y = 2
        split.operator(AddonUpdaterUpdateNow.bl_idname,
                       text="Update directly to " + str(Updater.include_branch_list[0]))
        split = subcol.split(align=True)
        split.scale_y = 2
        split.operator(AddonUpdaterCheckNow.bl_idname, text="", icon="FILE_REFRESH")

    elif Updater.update_ready is True and Updater.manual_only is False:
        subcol = col.row(align=True)
        subcol.scale_y = 1
        split = subcol.split(align=True)
        split.scale_y = 2
        split.operator(AddonUpdaterUpdateNow.bl_idname,
                       text="Update now to " + str(Updater.update_version))
        split = subcol.split(align=True)
        split.scale_y = 2
        split.operator(AddonUpdaterCheckNow.bl_idname, text="", icon="FILE_REFRESH")

    elif Updater.update_ready is True and Updater.manual_only is True:
        col.scale_y = 2
        col.operator("wm.url_open", text="Download " + str(Updater.update_version)).url = Updater.website
    else:
        subcol = col.row(align=True)
        subcol.scale_y = 1
        split = subcol.split(align=True)
        split.enabled = False
        split.scale_y = 2
        split.operator(AddonUpdaterCheckNow.bl_idname, text="Addon is up to date")
        split = subcol.split(align=True)
        split.scale_y = 2
        split.operator(AddonUpdaterCheckNow.bl_idname, text="", icon="FILE_REFRESH")

    row = element.row()
    row.prop(settings, "auto_check_update")

    row = element.row()
    row.scale_y = 0.7
    lastcheck = Updater.json["last_check"]
    if Updater.error is not None and Updater.error_msg is not None:
        row.label(text=Updater.error_msg)
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
    if not isinstance(tupled, tuple):
        return True

    if self.version_min_update is not None:
        if tupled < self.version_min_update:
            return True

    if self.version_max_update is not None:
        if tupled >= self.version_max_update:
            return True

    return False


def select_link_function(tag):
    link = tag["zipball_url"]
    return link


classes = (
    AddonUpdaterInstallPopup,
    AddonUpdaterCheckNow,
    AddonUpdaterUpdateNow,
    AddonUpdaterUpdateTarget,
    AddonUpdaterInstallManually,
    AddonUpdaterUpdatedSuccessful,
    AddonUpdaterRestoreBackup,
    AddonUpdaterIgnore,
    AddonUpdaterEndBackground
)


def register(bl_info):
    if Updater.error:
        print("Exiting updater registration, " + Updater.error)
        return
    Updater.clear_state()
    Updater.engine = "Github"
    Updater.private_token = None
    Updater.user = "Grim-es"
    Updater.repo = "material-combiner-addon"
    Updater.website = "https://github.com/Grim-es/material-combiner-addon/archive/master.zip"
    Updater.subfolder_path = ""
    Updater.current_version = bl_info["version"]
    Updater.verbose = False
    Updater.backup_current = False
    Updater.backup_ignore_patterns = ["*"]
    Updater.overwrite_patterns = ["*"]
    Updater.remove_pre_update_patterns = ["*"]
    Updater.include_branches = False
    Updater.use_releases = False
    Updater.include_branch_list = None
    Updater.manual_only = False
    Updater.fake_install = False
    Updater.showpopups = True
    Updater.version_min_update = (1, 1, 6, 4)
    Updater.version_max_update = None
    Updater.skip_tag = skip_tag_function
    Updater.select_link = select_link_function

    for cls in classes:
        make_annotations(cls)
        bpy.utils.register_class(cls)

    show_reload_popup()


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    Updater.clear_state()

    global ran_autocheck_install_popup
    ran_autocheck_install_popup = False

    global ran_update_sucess_popup
    ran_update_sucess_popup = False

    global ran_background_check
    ran_background_check = False
