# Copyright (c) 2014-2015 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from gi.repository import Gtk, GLib

from lollypop.define import Lp


class View(Gtk.Grid):
    """
        Generic view
    """

    def __init__(self):
        """
            Init view
        """
        Gtk.Grid.__init__(self)
        self.set_property('orientation', Gtk.Orientation.VERTICAL)
        self.set_border_width(0)
        self._current_signal = Lp.player.connect('current-changed',
                                                 self._on_current_changed)
        self._cover_signal = Lp.art.connect('cover-changed',
                                            self._on_cover_changed)
        self._scan_signal = Lp.scanner.connect('album-modified',
                                               self._on_album_modified)

        # Stop populate thread
        self._stop = False
        self._new_ids = []

        self._scrolledWindow = Gtk.ScrolledWindow()
        self._scrolledWindow.set_policy(Gtk.PolicyType.NEVER,
                                        Gtk.PolicyType.AUTOMATIC)

        self._scrolledWindow.show()
        self._viewport = Gtk.Viewport()
        self._scrolledWindow.add(self._viewport)
        self._viewport.show()

    def remove_signals(self):
        """
            Remove signals on player object
        """
        if self._current_signal:
            Lp.player.disconnect(self._current_signal)
            self._current_signal = None
        if self._cover_signal:
            Lp.art.disconnect(self._cover_signal)
            self._cover_signal = None
        if self._scan_signal:
            Lp.scanner.disconnect(self._scan_signal)
            self._scan_signal = None

    def stop(self):
        """
            Stop populating
        """
        self._stop = True
        for child in self._get_children():
            child.stop()

    def update_covers(self):
        """
            Update children's covers
        """
        GLib.idle_add(self._update_widgets, self._get_children(), True)

#######################
# PRIVATE             #
#######################
    def _update_widgets(self, widgets, force):
        """
            Update all widgets
            @param widgets as AlbumWidget
            @param force as bool
        """
        if widgets:
            widget = widgets.pop(0)
            widget.set_cover(force)
            widget.update_cursor()
            widget.update_playing_indicator()
            GLib.idle_add(self._update_widgets, widgets, force)

    def _get_children(self):
        """
            Return view children
        """
        return []

    def _on_cover_changed(self, widget, album_id):
        """
            Update album cover in view
            @param widget as unused, album id as int
        """
        for widget in self._get_children():
            widget.update_cover(album_id)

    def _on_current_changed(self, player):
        """
            Current song changed
            @param player as Player
        """
        GLib.idle_add(self._update_widgets, self._get_children(), False)

    def _on_album_modified(self, scanner, album_id):
        """
            On album modified, disable it
            @param scanner as CollectionScanner
            @param album id as int
        """
        for child in self._get_children():
            if album_id == child.get_id():
                child.set_sensitive(False)
