#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Leviathan Music Player
# A Web-based music player based on the Leviathan music library manager.
# 
# Copyright (C) 2010-2011 Scott Zeid
# http://me.srwz.us/leviathan/web
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
# 
# Except as contained in this notice, the name(s) of the above copyright holders
# shall not be used in advertising or otherwise to promote the sale, use or
# other dealings in this Software without prior written authorization.

import base64
import datetime
import hashlib
import os
import stat
import string
import time

from decimal import Decimal
from StringIO import StringIO
from urllib import quote

from PIL import Image
import yaml

try:
 from gevent import monkey, pywsgi
 GEVENT = True
except ImportError:
 GEVENT = False

from jugofpunch import *
import leviathan
import pylast

config(root=__file__)

config.name = "Leviathan Music Player"
config.template.defaults = dict(
 settings=lambda: settings(),
 theme=lambda: theme(),
 url_scheme=lambda: url_scheme()
)

artwork_cache_dir = os.path.join(config.root, "artwork-cache")
generic_artwork_cache_dir = os.path.join(artwork_cache_dir, "generic")
library_artwork_cache_dir = os.path.join(artwork_cache_dir, "library")

LAST_FM_API_KEY    = "564bfe2575a418e90e6977cfc71d7fbe"
LAST_FM_API_SECRET = "164dd907b69d8b50d047ba66d233249e"
SETTINGS_FILE      = "webleviathan.yaml"

class _GeventServer(ServerAdapter):
 def run(self, handler):
  monkey.patch_all()
  pywsgi.WSGIServer((self.host, self.port), handler).serve_forever()

@route("/artwork/:relpath#.*#/:mode.png")
@route("/generic-artwork/:mode.png")
def artwork(relpath=None, mode="album"):
 side_length = int(request.GET.get("size", "0"))
 image_path = None
 generic = False
 if relpath:
  relpath = relpath
  if mode == "artist":
   image_path = get_artist_art_relpath(relpath, side_length)
  else:
   image_path = get_album_art_relpath(relpath, side_length)
 if not image_path:
  if mode == "artist":
   raise HTTPError(404)
  artwork_filename = "artwork.%d.png" % side_length
  if os.path.isfile(os.path.realpath(os.path.join(generic_artwork_cache_dir,
                                                  artwork_filename))):
   image_path = os.path.join(generic_artwork_cache_dir, artwork_filename)
  else:
   image_path = os.path.join(config.root, "images", "generic-artwork-8th.png")
  generic = True
 if not image_path.startswith(artwork_cache_dir):
  response.content_type = "image/png"
  return cache_artwork(image_path, side_length, generic=generic)
 else:
  return static_file(os.path.basename(image_path), os.path.dirname(image_path))

def cache_artwork(image_path, side_length, generic=False):
 if not generic and not image_path.startswith(library.library.encode("utf-8")):
  raise ValueError("image_path must be within the library root")
 cache_dir = generic_artwork_cache_dir if generic else library_artwork_cache_dir
 cache_dir = cache_dir.encode("utf-8")
 if generic:
  save_path = os.path.join(cache_dir, "artwork.%d.png" % side_length)
 else:
  relpath = os.path.dirname(os.path.relpath(image_path,
                                            library.library.encode("utf-8")))
  save_path = os.path.join(cache_dir, relpath, "artwork.%d.png" % side_length)
 if not os.path.isdir(os.path.realpath(os.path.dirname(save_path))):
  os.makedirs(os.path.realpath(os.path.dirname(save_path)),
              stat.S_IRWXU|stat.S_IRGRP|stat.S_IXGRP|stat.S_IROTH|stat.S_IXOTH)
 im = Image.open(image_path)
 im_str = StringIO()
 width, height = im.size
 if not side_length or (width <= side_length and height <= side_length):
  im.save(im_str, "PNG")
 else:
  if width < height:
   width = int(round(Decimal(side_length * width) / Decimal(height)))
   height = side_length
  elif width > height:
   height = int(round(Decimal(side_length * height) / Decimal(width)))
   width = side_length
  else:
   width, height = side_length, side_length
  im = im.resize((width, height), Image.ANTIALIAS)
  im.save(im_str, "PNG")
 im_str = im_str.getvalue()
 with open(save_path, "w") as f:
  f.write(im_str)
 return im_str

def get_album_art_relpath(relpath, side_length=0):
 image_path = None
 cache_filename = "artwork.%d.png" % side_length
 if relpath:
  for d in ((library_artwork_cache_dir.encode("utf-8"), True),
            (library.library.encode("utf-8"), False)):
   path = os.path.join(d[0], relpath)
   for p in (path, os.path.dirname(path)):
    p = os.path.join(p, path)
    if os.path.isdir(os.path.realpath(p)):
     l = sorted(os.listdir(p))
     if d[1]:
      if side_length and \
         os.path.isfile(os.path.realpath(os.path.join(p, cache_filename))):
       image_path = os.path.join(p, cache_filename)
      continue
     for i in l:
      if os.path.isfile(os.path.realpath(os.path.join(p, i))) and \
         (i.lower().endswith(".png") or i.lower().endswith(".jpg") or
          i.lower().endswith(".gif")):
       image_path = os.path.join(p, i)
       break
    if image_path:
     break
   if image_path:
    break
 return image_path

def get_artist_art_relpath(relpath, side_length=0):
 image_path = None
 cache_filename = "artwork.%d.png" % side_length
 if relpath:
  for d in ((library_artwork_cache_dir.encode("utf-8"), True),
            (library.library.encode("utf-8"), False)):
   p = os.path.join(d[0], [i for i in os.path.split(relpath) if i][0])
   if os.path.isdir(os.path.realpath(p)):
    l = sorted(os.listdir(p))
    if d[1]:
     if side_length and \
        os.path.isfile(os.path.realpath(os.path.join(p, cache_filename))):
      image_path = os.path.join(p, cache_filename)
     continue
    for i in l:
     if os.path.isfile(os.path.realpath(os.path.join(p, i))) and \
        (i.lower().endswith(".png") or i.lower().endswith(".jpg") or
         i.lower().endswith(".gif")):
      image_path = os.path.join(p, i)
      break
   if image_path:
    break
 return image_path

def get_list(category, id=None, queue=None):
 # Format: (id, name)
 # id is the same as name for artists and albums
 if category == "queue":
  queue = queue if queue != None else request.GET.get("queue", "").split(",")
  l = [library.get_song(int(i)) for i in queue if i != ""]
  return [(i[0], i[1].title, i[1]) for i in l]
 elif category == "artist":
  return [(i[0], i[1].title, i[1]) for i in library.get_artist(id)]
 elif category == "artists":
  return [(i, i, None) for i in library.get_artists()]
 elif category == "album":
  return [(i[0], i[1].title, i[1]) for i in library.get_album(id[0], id[1])]
 elif category == "albums":
  return [("%s_%s" % tuple(i),
           i[1] if id else "%s - %s"%(i[1] or "(Unknown)", i[0] or "(Unknown)"),
           i) for i in library.get_albums(id)]
 elif category == "playlist":
  return [(i[0], i[1].title, i[1]) for i in library.get_playlist(int(id))]
 elif category == "playlists":
  return [(i[0], i[1], None) for i in library.get_playlists()]
 elif category == "song":
  return [(i[0], i[1].title, i[1]) for i in [library.get_song(int(id))]]
 elif category == "songs":
  return [(i[0], i[1].title, i[1]) for i in library.get_songs()]

@route("/")
@view("index")
def index():
 return dict()

def last_fm_login():
 cfg = settings()["last.fm"];
 return pylast.LastFMNetwork(api_key=LAST_FM_API_KEY,
                             api_secret=LAST_FM_API_SECRET,
                             username=cfg["username"],
                             password_hash=pylast.md5(cfg["password"]))

@route("/library/:relpath#.*#")
def library(relpath):
 relpath = relpath
 if not relpath.lower().endswith(".mp3"):
  relpath = os.path.splitext(relpath)[0] + ".mp3"
 basename = os.path.basename(relpath)
 directory = os.path.dirname(os.path.join(library.library.encode("utf-8"),
                                          relpath))
 return static_file(basename, directory)

def list_category(category, format=""):
 artist, id = request.GET.get("artist"), request.GET.get("id")
 artist = to_unicode(artist) if artist != None else artist
 id = to_unicode(id) if id != None else id
 parent = request.GET.get("parent")
 if category == "album":
  id = (artist, id)
 if id != None and category not in ("artist", "album", "albums", "playlist",
                                    "song"):
  id = None
 if category in ("queue", "artist", "artists", "album", "albums", "playlist",
                 "playlists", "song", "songs"):
  l = []
  for i in get_list(category, id):
   quoted_id = quote(to_unicode(i[0]).encode("utf-8"), "")
   dom_id = (parent+"_" if parent else "")+"%s_entry_%s" % (category,quoted_id)
   dom_id = category + "_" + hashlib.sha1(dom_id).hexdigest()
   info = ((i[2] if isinstance(i[2], leviathan.Song) else
            [quote(to_unicode(j).encode("utf-8"), "") for j in i[2]])
           if i[2] else None)
   name = full_name = to_unicode(i[1]) if i[1] else "(Unknown)"
   if category in ("artist", "album", "playlist", "queue", "song", "songs"):
    full_name = u"%s — %s" % (i[1] or "(Unknown)",
                              (info.artist or "(Unknown)") if i else "")
    if category != "album":
     name = full_name
   icon = ""
   if isinstance(i[2], leviathan.Song):
    relpath = i[2].relpath
    if not relpath.lower().endswith(".mp3"):
     relpath = os.path.splitext(relpath)[0] + ".mp3"
    url = root_url() + "/library/" + quote(relpath.encode("utf-8"))
    art_relpath = os.path.dirname(relpath)
    art_url = root_url() + "/artwork/" + quote(art_relpath.encode("utf-8"))
    song = dict(relpath=i[2].relpath, title=i[2].title, artist=i[2].artist,
                album=i[2].album, url=url, art_directory=art_url)
    icon = art_url + "/album.png?size=16"
   else:
    song = None
   if category == "albums":
    try:
     art_relpath = os.path.dirname(library.get_album(*i[2])[0][1].relpath)
     art_url = root_url() + "/artwork/" + quote(art_relpath.encode("utf-8"))
     icon = art_url + "/album.png?size=16"
    except (IndexError, TypeError):
     icon = root_url() + "/generic-artwork/album.png?size=16"
   l.append(dict(
    dom_id=dom_id, name=name, full_name=full_name, song=song, icon=icon,
    data_id=info[1] if category == "albums" else quoted_id,
    data_artist=info[0] if category == "albums" else ""
   ))
  return dict(category=category, artist=artist, id=id, entries=l, parent=parent)
 else:
  return ""

@route("/list/:category/fragment.html")
@view("fragment.html")
def list_category_html_fragment(category):
 return list_category(category, "html_fragment")

@route("/list/:category/list.json")
def list_category_json(category):
 return list_category(category, "json")

@route("/list/:category/xspf.xml")
@view("xspf.xml")
def list_category_xspf(category):
 return list_category(category, "xspf")

@route("/scrobble/:id")
def scrobble(id):
 timestamp = int(request.GET.get("timestamp", round(time.time())))
 song = library.get_song(int(id))[1]
 lfm = last_fm_login()
 if song.artist and song.title:
  optional = {}
  if song.album:
   optional["album"] = song.album
  duration = request.GET.get("duration", None)
  if duration != None:
   optional["duration"] = int(duration)
  lfm.scrobble(song.artist, song.title, timestamp, **optional)

def settings():
 return load_yaml_file(SETTINGS_FILE)

@route("/style.css")
@view("style.css")
def style_css():
 response.content_type = "text/css"
 return dict()

def theme():
 selected_theme = settings()["theme"]
 return load_yaml_file(os.path.join("themes", selected_theme + ".yaml"))

def to_unicode(s, encoding="utf8"):
 if isinstance(s, unicode):
  return s
 if isinstance(s, (str, buffer)):
  return unicode(s, encoding)
 return unicode(s)

@route("/update-now-playing/:id")
def update_now_playing(id):
 song = library.get_song(int(id))[1]
 lfm = last_fm_login()
 if song.artist and song.title:
  optional = {}
  if song.album:
   optional["album"] = song.album
  duration = request.GET.get("duration", "")
  if duration != "":
   optional["duration"] = int(duration)
  lfm.update_now_playing(song.artist, song.title, **optional)

@route("/webleviathan.js")
@view("webleviathan.js")
def webleviathan_js():
 response.content_type = "text/javascript"
 return dict()

@error(403)
@view("error")
def error_403(unknown):
 return dict(content="You don't have permission to view this page.", action="error")

@error(404)
@view("error")
def error_404(unknown):
 return dict(content="The page you were looking for was not found.", action="error")

leviathan_cfg_path = to_unicode(settings()["leviathan.yaml"])
leviathan_cfg_path = os.path.normpath(os.path.expanduser(leviathan_cfg_path))
library = leviathan.Library(leviathan_cfg_path)

application = app()

if GEVENT:
 run_if_main(__name__, True, server=_GeventServer)
else:
 run_if_main(__name__, True)
