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

from gi.repository import GLib, GdkPixbuf, Gio

import re
import os

from lollypop.art_base import BaseArt


class RadioArt(BaseArt):
    """
        Manage radio artwork
    """
    _RADIOS_PATH = os.path.expanduser("~") +\
        "/.local/share/lollypop/radios"

    def __init__(self):
        """
            Init radio art
        """
        BaseArt.__init__(self)
        if not os.path.exists(self._RADIOS_PATH):
            try:
                os.mkdir(self._RADIOS_PATH)
            except:
                print("Can't create %s" % self._RADIOS_PATH)

    def get_radio_cache_path(self, name, size):
        """
            get cover cache path for radio
            @param name as string
            @return cover path as string or None if no cover
        """
        filename = ''
        try:
            filename = self._get_radio_cache_name(name)
            cache_path_jpg = "%s/%s_%s.png" % (self._CACHE_PATH,
                                               filename,
                                               size)
            if os.path.exists(cache_path_jpg):
                return cache_path_jpg
            else:
                self.get_radio(name, size)
                if os.path.exists(cache_path_jpg):
                    return cache_path_jpg
                else:
                    return None
        except Exception as e:
            print("Art::get_radio_cache_path(): %s" % e, ascii(filename))
            return None

    def get_radio(self, name, size, selected=False):
        """
            Return a cairo surface for radio name
            @param radio name as string
            @param pixbuf size as int
            @param selected as bool
            @return cairo surface
        """
        scaled_size =  size * self._nullwidget.get_scale_factor()
        filename = self._get_radio_cache_name(name)
        cache_path_png = "%s/%s_%s.png" % (self._CACHE_PATH,
                                           filename,
                                           scaled_size)
        pixbuf = None

        try:
            # Look in cache
            if os.path.exists(cache_path_png):
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(cache_path_png,
                                                                scaled_size,
                                                                scaled_size)
            else:
                pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB,
                                              True,
                                              8,
                                              scaled_size,
                                              scaled_size)
                pixbuf.fill(0xffffffff)
                path = self._get_radio_art_path(name)
                if path is not None:
                    cover = GdkPixbuf.Pixbuf.new_from_file_at_size(path,
                                                                   scaled_size,
                                                                   scaled_size)
                    cover_width = cover.get_width()
                    cover_height = cover.get_height()
                    cover.composite(pixbuf,
                                    (scaled_size-cover_width)/2,
                                    (scaled_size-cover_height)/2,
                                    cover_width,
                                    cover_height,
                                    (scaled_size-cover_width)/2,
                                    (scaled_size-cover_height)/2,
                                    1,
                                    1,
                                    GdkPixbuf.InterpType.HYPER,
                                    255)

            if pixbuf is None:
                pixbuf = self._get_default_icon(
                    scaled_size,
                    'audio-input-microphone-symbolic')

            # Gdk < 3.15 was missing save method
            # > 3.15 is missing savev method
            try:
                pixbuf.save(cache_path_png, "png",
                            [None], [None])
            except:
                pixbuf.savev(cache_path_png, "png",
                             [None], [None])
            return self._make_icon_frame(pixbuf, size, selected)

        except Exception as e:
            print(e)
            return self._make_icon_frame(self._get_default_icon(
                                         scaled_size,
                                         'audio-input-microphone-symbolic'),
                                         size,
                                         selected)

    def copy_uri_to_cache(self, uri, name, size):
        """
            Copy uri to cache at size
            @param uri as string
            @param name as string
            @param size as int
            @thread safe
        """
        filename = self._get_radio_cache_name(name)
        cache_path_png = "%s/%s_%s.png" % (self._CACHE_PATH, filename, size)
        s = Gio.File.new_for_uri(uri)
        d = Gio.File.new_for_path(cache_path_png)
        s.copy(d, Gio.FileCopyFlags.OVERWRITE, None, None)
        GLib.idle_add(self.emit, 'logo-changed', name)

    def save_radio_logo(self, pixbuf, radio):
        """
            Save pixbuf for radio
            @param pixbuf as Gdk.Pixbuf
            @param radio name as string
        """
        try:
            artpath = self._RADIOS_PATH + "/" +\
                      radio.replace('/', '-') + ".png"

            # Gdk < 3.15 was missing save method
            try:
                pixbuf.save(artpath, "png", [None], [None])
            # > 3.15 is missing savev method :(
            except:
                pixbuf.savev(artpath, "png", [None], [None])
        except Exception as e:
            print("Art::save_radio_logo(): %s" % e)

    def announce_logo_update(self, name):
        """
            Announce radio logo update
            @param radio name as string
        """
        self.emit('logo-changed', name)

    def clean_radio_cache(self, name):
        """
            Remove logo from cache for radio
            @param radio name as string
        """
        filename = self._get_radio_cache_name(name)
        try:
            for f in os.listdir(self._CACHE_PATH):
                if re.search('%s_.*\.png' % re.escape(filename), f):
                    os.remove(os.path.join(self._CACHE_PATH, f))
        except Exception as e:
            print("Art::clean_radio_cache(): ", e, filename)

#######################
# PRIVATE             #
#######################
    def _get_radio_art_path(self, name):
        """
            Look for radio covers
            @param radio name as string
            @return cover file path as string
        """
        try:
            name = name.replace('/', '-')
            if os.path.exists(self._RADIOS_PATH + "/" + name + ".png"):
                return self._RADIOS_PATH + "/" + name + ".png"
            return None
        except Exception as e:
            print("Art::_get_radio_art_path(): %s" % e)

    def _get_radio_cache_name(self, name):
        """
            Get a uniq string for radio
            @param album id as int
            @param sql as sqlite cursor
        """
        return "@@"+name.replace('/', '-')+"@@radio@@"
