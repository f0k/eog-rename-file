# Rename file plugin for Eye of GNOME
# -*- encoding: utf-8 -*-
# Copyright (C) 2022 Jan Schlüter
# Based on eogtricks-bracket-tags by Andrew Chadwick
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

from __future__ import print_function

import os
import logging
import bisect

from gi.repository import Eog
from gi.repository import GObject
from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import Pango
from gi.repository import GLib


logger = logging.getLogger(__name__)
if os.environ.get("EOGPLUGIN_DEBUG"):
    logging.basicConfig(level=logging.DEBUG)

FORBIDDEN_ENTRY_CHARS = {'/'}


def check_entry_text(widget, string, len, pos):
    for c in string:
        if c in FORBIDDEN_ENTRY_CHARS:
            widget.stop_emission_by_name('insert-text')


def show_rename_dialog(window, old_name, new_name=None):
    if new_name is None:
        new_name = old_name

    flags = Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT
    dialog = Gtk.Dialog(
        "Rename File",
        window,
        flags,
        buttons=[
            "Cancel", Gtk.ResponseType.REJECT,
            "OK", Gtk.ResponseType.ACCEPT,
        ],
    )
    dialog.set_position(Gtk.WindowPosition.MOUSE)
    dialog.set_default_response(Gtk.ResponseType.ACCEPT)
    dialog.set_border_width(8)

    entry = Gtk.Entry()
    entry.set_text(new_name)
    entry.set_activates_default(True)
    entry.set_input_purpose(Gtk.InputPurpose.FREE_FORM)
    hints = Gtk.InputHints.SPELLCHECK | Gtk.InputHints.LOWERCASE
    entry.set_input_hints(hints)
    entry.connect('insert-text', check_entry_text)
    entry.grab_focus()
    entry.set_size_request(400, -1)
    basename, ext = os.path.splitext(new_name)
    GLib.idle_add(entry.select_region, 0, len(basename))

    label = Gtk.Label("Rename “%s” to:" % old_name)
    label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)

    dialog.vbox.pack_start(label, 1, 1, 4)
    dialog.vbox.pack_start(entry, 0, 0, 8)

    entry.show()
    label.show()

    try:
        response = dialog.run()
        if response != Gtk.ResponseType.ACCEPT:
            return None
        else:
            return entry.get_text()
    finally:
        dialog.destroy()


def show_retry_dialog(window, error):
    flags = Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT
    dialog = Gtk.Dialog(
        "Rename Failed",
        window,
        flags,
        buttons=[
            "Abort", Gtk.ResponseType.REJECT,
            "Enter new name", Gtk.ResponseType.ACCEPT,
        ],
    )
    dialog.set_position(Gtk.WindowPosition.MOUSE)
    dialog.set_default_response(Gtk.ResponseType.ACCEPT)
    dialog.set_border_width(8)

    label = Gtk.Label(error)
    label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
    dialog.vbox.pack_start(label, 0, 0, 8)
    label.show()

    try:
        return (dialog.run() == Gtk.ResponseType.ACCEPT)
    finally:
        dialog.destroy()


def get_image_filename(img):
    file = img.get_file()
    flags = Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS
    attrs = Gio.FILE_ATTRIBUTE_STANDARD_EDIT_NAME
    fileinfo = file.query_info(attrs, flags)
    return fileinfo.get_edit_name()


class FileRenamer(GObject.GObject, Eog.WindowActivatable):

    ACTION_NAME = "rename-file"

    window = GObject.property(type=Eog.Window)

    def __init__(self):
        super().__init__()
        self.action = Gio.SimpleAction(name=self.ACTION_NAME)
        self.action.connect("activate", self._action_activated_cb)

    def do_activate(self):
        logger.debug("Activated. Adding action win.%s", self.ACTION_NAME)
        self.window.add_action(self.action)
        app = self.window.get_application()
        app.set_accels_for_action(
            "win." + self.ACTION_NAME,
            ["F2"],
        )

    def do_deactivate(self):
        logger.debug("Deactivated. Removing action win.%s", self.ACTION_NAME)
        self.window.remove_action(self.ACTION_NAME)

    def _action_activated_cb(self, action, param):
        img = self.window.get_image()
        if not img:
            return
        if not img.is_file_writable():
            return

        old_name = get_image_filename(img)
        new_name = None

        while True:
            new_name = show_rename_dialog(self.window, old_name, new_name)
            if new_name is not None and new_name != old_name:
                # Rename the image by setting its GFile's display name.
                logger.debug("Rename '%s' → '%s'", old_name, new_name)
                store = self.window.get_store()
                old_pos = store.get_pos_by_image(img)
                try:
                    img.get_file().set_display_name(new_name)
                except GLib.GError as exc:
                    logger.debug(exc.args[0])
                    if show_retry_dialog(self.window, exc.args[0]):
                        continue
                else:
                    # Find and jump to the renamed image.
                    GLib.idle_add(self._set_current_idle_cb, old_pos, new_name)
            break

    def _set_current_idle_cb(self, pos, new_name):
        # Jump to the new location of the renamed image. There is no API for
        # that, so we use binary search to find it in the alphabetic store.
        view = self.window.get_thumb_view()
        store = self.window.get_store()

        def get_filename(i):
            return get_image_filename(store.get_image_by_pos(i))

        # It is not unlikely the file is at the same position, so we start there:
        name = get_filename(pos)
        if name < new_name:
            pos = bisect.bisect_left(range(store.length()), new_name, lo=pos, key=get_filename)
        elif name > new_name:
            pos = bisect.bisect_left(range(pos), new_name, key=get_filename)
        
        view.set_current_image(store.get_image_by_pos(pos), True)
        return False

    def _print_accels(self):
        app = self.window.get_application()
        for detailed_name in app.list_action_descriptions():
            print(detailed_name, end=", ")
            print(app.get_accels_for_action(detailed_name))
