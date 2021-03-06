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

from gi.repository import Gtk, Gdk, GLib, Gio, GdkPixbuf

from _thread import start_new_thread
from gettext import gettext as _

from lollypop.objects import Album
from lollypop.define import Lp, ArtSize, GOOGLE_INC, GOOGLE_MAX


class CoversPopover(Gtk.Popover):
    """
        Popover with album covers from the web
    """

    def __init__(self, artist_id, album_id):
        """
            Init Popover
            @param artist id as int
            @param album id as int
        """
        Gtk.Popover.__init__(self)
        self._album = Album(album_id)
        self._start = 0
        self._orig_pixbufs = {}

        self._stack = Gtk.Stack()
        self._stack.show()

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/CoversPopover.ui')

        widget = builder.get_object('widget')
        widget.add(self._stack)

        self._view = Gtk.FlowBox()
        self._view.set_selection_mode(Gtk.SelectionMode.NONE)
        self._view.connect('child-activated', self._on_activate)
        self._view.set_max_children_per_line(100)
        self._view.set_property('row-spacing', 10)
        self._view.show()

        self._label = builder.get_object('label')
        self._label.set_text(_("Please wait..."))

        builder.get_object('viewport').add(self._view)

        self._scrolled = builder.get_object('scrolled')
        spinner = builder.get_object('spinner')
        self._not_found = builder.get_object('notfound')
        self._stack.add(spinner)
        self._stack.add(self._not_found)
        self._stack.add(self._scrolled)
        self._stack.set_visible_child(spinner)
        self.add(widget)

    def populate(self):
        """
            Populate view
        """
        # First load local files
        self._urls = Lp.art.get_locally_available_covers(self._album)
        for url in self._urls:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(url,
                                                            ArtSize.MONSTER,
                                                            ArtSize.MONSTER)
            self._add_pixbuf(pixbuf)
        if len(self._urls) > 0:
            self._stack.set_visible_child(self._scrolled)
        # Then Google files
        self._thread = True
        self._start = 0
        start_new_thread(self._populate, ())

    def do_show(self):
        """
            Resize popover and set signals callback
        """
        self.set_size_request(700, 400)
        Gtk.Popover.do_show(self)

    def do_hide(self):
        """
            Kill thread
        """
        self._thread = False
        Gtk.Popover.do_hide(self)

#######################
# PRIVATE             #
#######################
    def _populate(self):
        """
            Same as populate()
        """
        self._urls = []
        if Gio.NetworkMonitor.get_default().get_network_available():
            self._urls = Lp.art.get_google_arts("%s+%s" % (
                                                       self._album.artist_name,
                                                       self._album.name))
        if self._urls:
            self._start += GOOGLE_INC
            self._add_pixbufs()
        else:
            GLib.idle_add(self._show_not_found)

    # FIXME Do not use recursion
    def _add_pixbufs(self):
        """
            Add urls to the view
        """
        if self._urls:
            url = self._urls.pop()
            stream = None
            try:
                f = Gio.File.new_for_uri(url)
                (status, data, tag) = f.load_contents()
                if status:
                    stream = Gio.MemoryInputStream.new_from_data(data, None)
            except:
                if self._thread:
                    self._add_pixbufs()
            if stream is not None:
                GLib.idle_add(self._add_stream, stream)
            if self._thread:
                self._add_pixbufs()
        elif self._start < GOOGLE_MAX:
            self._populate()

    def _show_not_found(self):
        """
            Show not found message
        """
        if len(self._view.get_children()) == 0:
            self._label.set_text(_("No cover found..."))
            self._stack.set_visible_child(self._not_found)

    def _add_stream(self, stream):
        """
            Add stream to the view
            @param stream as Gio.MemoryInputStream
        """
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(
                stream, ArtSize.MONSTER,
                ArtSize.MONSTER,
                False,
                None)
            self._add_pixbuf(pixbuf)
        except Exception as e:
            print(e)
            pass
        # Remove spinner if exist
        if self._scrolled != self._stack.get_visible_child():
            self._label.set_text(_("Select a cover art for this album"))
            self._stack.set_visible_child(self._scrolled)

    def _add_pixbuf(self, pixbuf):
        """
            Add pixbuf to the view
            @param pixbuf as Gdk.Pixbuf
        """
        image = Gtk.Image()
        self._orig_pixbufs[image] = pixbuf
        scaled_pixbuf = pixbuf.scale_simple(
            ArtSize.BIG*self.get_scale_factor(),
            ArtSize.BIG*self.get_scale_factor(),
            2)
        del pixbuf
        surface = Gdk.cairo_surface_create_from_pixbuf(scaled_pixbuf,
                                                       0,
                                                       None)
        del scaled_pixbuf
        image.set_from_surface(surface)
        del surface
        image.show()
        self._view.add(image)

    def _on_activate(self, flowbox, child):
        """
            Use pixbuf as cover
            Reset cache and use player object to announce cover change
        """
        pixbuf = self._orig_pixbufs[child.get_child()]
        Lp.art.save_album_art(pixbuf, self._album.id)
        Lp.art.clean_album_cache(self._album.id)
        Lp.art.announce_cover_update(self._album.id)
        self.hide()
        self._streams = {}
