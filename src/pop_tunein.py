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

from gi.repository import Gtk, GLib, Gio

from _thread import start_new_thread
from gettext import gettext as _

from lollypop.tunein import TuneIn
from lollypop.define import Lp, ArtSize
from lollypop.art import Art


class TuneinPopover(Gtk.Popover):
    """
        Popover showing tunin radios
    """

    def __init__(self, radio_manager):
        """
            Init Popover
            @param radio manager as RadioManager
        """
        Gtk.Popover.__init__(self)
        self._tunein = TuneIn()
        self._radio_manager = radio_manager
        self._current_url = None
        self._previous_urls = []
        self._current_items = []

        self._stack = Gtk.Stack()
        self._stack.set_property('expand', True)
        self._stack.show()

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/TuneinPopover.ui')
        builder.connect_signals(self)
        widget = builder.get_object('widget')
        widget.attach(self._stack, 0, 2, 4, 1)

        self._back_btn = builder.get_object('back_btn')
        self._home_btn = builder.get_object('home_btn')
        self._label = builder.get_object('label')

        self._view = Gtk.FlowBox()
        self._view.set_selection_mode(Gtk.SelectionMode.NONE)
        self._view.set_max_children_per_line(100)
        self._view.set_property('row-spacing', 10)
        self._view.set_property('expand', True)
        self._view.show()

        builder.get_object('viewport').add(self._view)
        builder.get_object('viewport').set_property('margin', 10)

        self._scrolled = builder.get_object('scrolled')
        self._spinner = builder.get_object('spinner')
        self._not_found = builder.get_object('notfound')
        self._stack.add(self._spinner)
        self._stack.add(self._not_found)
        self._stack.add(self._scrolled)
        self._stack.set_visible_child(self._spinner)
        self.add(widget)

    def populate(self, url=None):
        """
            Populate views
            @param url as string
        """
        if not self._view.get_children():
            self._current_url = url
            self._clear()
            self._back_btn.set_sensitive(False)
            self._home_btn.set_sensitive(False)
            self._label.set_text(_("Please wait..."))
            start_new_thread(self._populate, (url,))

    def do_show(self):
        """
            Resize popover and set signals callback
        """
        size_setting = Lp.settings.get_value('window-size')
        if isinstance(size_setting[1], int):
            self.set_size_request(700, size_setting[1]*0.7)
        else:
            self.set_size_request(700, 400)
        Gtk.Popover.do_show(self)

#######################
# PRIVATE             #
#######################
    def _show_not_found(self):
        """
            Show not found message
        """
        self._label.set_text(_("Can't connect to TuneIn..."))
        self._stack.set_visible_child(self._not_found)
        self._home_btn.set_sensitive(True)

    def _populate(self, url):
        """
            Same as populate()
            @param url as string
            @thread safe
        """
        if url is None:
            self._current_items = self._tunein.get_items()
        else:
            self._current_items = self._tunein.get_items(url)

        if self._current_items:
            self._add_items()
        else:
            GLib.idle_add(self._show_not_found)

    def _add_items(self):
        """
            Add current items
            @thread safe
        """
        for item in self._current_items:
            GLib.idle_add(self._add_item, item)

    def _add_item(self, item):
        """
            Add item
            @param item as TuneItem
        """
        child = Gtk.Grid()
        child.set_property('halign', Gtk.Align.START)
        child.show()
        if item.TYPE == "audio":
            button = Gtk.Button.new_from_icon_name('list-add-symbolic',
                                                   Gtk.IconSize.MENU)
            button.connect('clicked', self._on_button_clicked, item)
            button.set_relief(Gtk.ReliefStyle.NONE)
            button.set_tooltip_text(_("Add"))
            button.show()
            child.add(button)

        link = Gtk.LinkButton.new_with_label(item.URL, item.TEXT)
        link.set_tooltip_text(_("Play"))
        link.connect('activate-link', self._on_activate_link, item)
        link.show()
        child.add(link)

        self._view.add(child)

        # Remove spinner if exist
        if self._spinner == self._stack.get_visible_child():
            self._stack.set_visible_child(self._scrolled)
            self._label.set_text(_("Browse themes and add a new radio"))
            if self._current_url is not None:
                self._back_btn.set_sensitive(True)
            self._home_btn.set_sensitive(True)

    def _clear(self):
        """
            Clear view
        """
        for child in self._view.get_children():
            self._view.remove(child)
            child.destroy()

    def _add_radio(self, item):
        """
            Add selected radio
            @param item as TuneIn Item
        """
        # Get cover art
        try:
            cache = Art._RADIOS_PATH
            s = Gio.File.new_for_uri(item.LOGO)
            d = Gio.File.new_for_path(cache+"/%s.png" %
                                      item.TEXT.replace('/', '-'))
            s.copy(d, Gio.FileCopyFlags.OVERWRITE, None, None)
        except Exception as e:
            print("TuneinPopover::_add_radio: %s" % e)
        url = item.URL
        # Tune in embbed uri in ashx files, so get content if possible
        try:
            f = Gio.File.new_for_uri(url)
            (status, data, tag) = f.load_contents()
            if status:
                url = data.decode('utf-8')
        except Exception as e:
            print("TuneinPopover::_add_radio: %s" % e)
        self._radio_manager.add(item.TEXT.replace('/', '-'))
        self._radio_manager.add_track(item.TEXT.replace('/', '-'),
                                      url)

    def _on_back_btn_clicked(self, btn):
        """
            Go to previous URL
            @param btn as Gtk.Button
        """
        url = None
        self._current_url = None
        if self._previous_urls:
            url = self._previous_urls.pop()
        self._stack.set_visible_child(self._spinner)
        self._clear()
        self.populate(url)

    def _on_home_btn_clicked(self, btn):
        """
            Go to root URL
            @param btn as Gtk.Button
        """
        self._current_url = None
        self._previous_urls = []
        self._stack.set_visible_child(self._spinner)
        self._clear()
        self.populate()

    def _on_activate_link(self, link, item):
        """
            Update header with new link
            @param link as Gtk.LinkButton
            @param item as TuneIn Item
        """
        if item.TYPE == "link":
            self._stack.set_visible_child(self._spinner)
            self._clear()
            self._scrolled.get_vadjustment().set_value(0.0)
            if self._current_url is not None:
                self._previous_urls.append(self._current_url)
            self.populate(item.URL)
        elif item.TYPE == "audio":
            for i in self._current_items:
                Lp.player.load_external(i.URL, i.TEXT)
            Lp.player.play_this_external(item.URL)
            # Only toolbar will get this one, so only create small in cache
            if Gio.NetworkMonitor.get_default().get_network_available():
                start_new_thread(Lp.art.copy_uri_to_cache, (item.LOGO,
                                                            item.TEXT,
                                                            ArtSize.SMALL))
        return True

    def _on_button_clicked(self, button, item):
        """
            Play the radio
            @param link as Gtk.Button
            @param item as TuneIn Item
        """
        start_new_thread(self._add_radio, (item,))
        self.hide()
