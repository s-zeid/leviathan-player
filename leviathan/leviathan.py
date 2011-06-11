#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Leviathan Music Manager
# A command-line utility to manage your music collection.
# 
# Copyright (C) 2010-2011 Scott Zeid
# http://me.srwz.us/leviathan
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

import collections
import os
import shutil
import sqlite3
import stat
import subprocess
import sys
import traceback

import mutagen
import yaml

from mutagen.easyid3 import EasyID3

Format = collections.namedtuple("Format", ["ffmpeg_codec"])
Song   = collections.namedtuple("Song", ["relpath", "title", "sort_title",
                                         "artist", "sort_artist", "album",
                                         "sort_album"])

DB_VERSION = "1"
EXTENSIONS = dict(
 aac  = Format("libfaac"),
 flac = Format("flac"),
 m4a  = Format("libfaac"),
 mp3  = Format("libmp3lame"),
 ogg  = Format("libvorbis"),
 wav  = Format("pcm_s16le"),
 wma  = Format("wmav2")
)

class Library:
 def __init__(self, config):
  if isinstance(config, basestring):
   with open(config, "rb") as f:
    config = yaml.load(f)
  elif isinstance(config, file):
   config = yaml.load(config)
  elif not isinstance(config, dict):
   raise ValueError("config must be a string, file object, or dict, not a "
                     + type(config).__name__)
  self.library = os.path.normpath(to_unicode(config["library"]))
  self.playlists = os.path.normpath(to_unicode(config["playlists"]))
  self.playlists_mp3 = os.path.normpath(to_unicode(config["playlists_mp3"]))
  self.playlist_db = os.path.normpath(to_unicode(config["playlist_db"]))
  self.albumart_filename = to_unicode(config["albumart_filename"])
  self.ffmpeg = to_unicode(config["ffmpeg"])
  self.lame = to_unicode(config["lame"])
  self.constant_bitrate = config["constant_bitrate"]
  if self.constant_bitrate != None:
   self.constant_bitrate = int(config["constant_bitrate"].lower().rstrip("k"))
  self.vbr_quality = config["vbr_quality"]
  if self.vbr_quality != None:
   self.vbr_quality = int(self.vbr_quality)
  self.db_ignore_playlists = to_unicode(config["db_ignore_playlists"])
 
 def _get_song_info(self, relpath):
  title, ext = os.path.splitext(os.path.basename(relpath))
  title = [title]
  artist = album = [""]
  fmt = get_format(ext)
  ret = None
  if fmt:
   cwd = os.getcwdu()
   os.chdir(self.library)
   if not os.path.isfile(os.path.realpath(relpath)):
    os.chdir(cwd)
    raise ValueError("The specified song does not exist or is not a regular"
                     " file or a link to one.")
   try:
    mg = mutagen.File(relpath, easy=True)
    if mg:
     title = to_unicode(mg.get("title", title)[0] if mg.get("title", title)[0] != ""
                                                  else title[0])
     sort_title = sort_value(title)
     artist = to_unicode(mg.get("artist", [""])[0])
     sort_artist = sort_value(artist)
     album = to_unicode(mg.get("album", [""])[0])
     sort_album = sort_value(album)
    ret = Song(relpath=to_unicode(relpath), title=title, sort_title=sort_title,
               artist=artist, sort_artist=sort_artist, album=album,
               sort_album=sort_album)
   finally:
    os.chdir(cwd)
  return ret
 
 def _setup_db(self):
  new = False if os.path.exists(os.path.realpath(self.playlist_db)) else True
  conn = sqlite3.connect(self.playlist_db)
  c = conn.cursor()
  if new:
   schema = """\
CREATE TABLE "leviathan_meta" (
 "id"          integer NOT NULL PRIMARY KEY,
 "key"         text    NOT NULL,
 "value"       text    NOT NULL
);

CREATE TABLE "songs" (
 "id"          integer NOT NULL PRIMARY KEY,
 "relpath"     text    NOT NULL UNIQUE,
 "title"       text    NOT NULL,
 "sort_title"  text    NOT NULL,
 "artist"      text    NOT NULL,
 "sort_artist" text    NOT NULL,
 "album"       text    NOT NULL,
 "sort_album"  text    NOT NULL
);

CREATE TABLE "playlists" (
 "id"          integer NOT NULL PRIMARY KEY,
 "name"        text    NOT NULL UNIQUE
);

CREATE TABLE "playlist_entries" (
 "id"          integer NOT NULL PRIMARY KEY,
 "song"        integer NOT NULL,
 "playlist"    integer NOT NULL
);

CREATE INDEX "playlist_entries_song"     ON "playlist_entries" ("song");
CREATE INDEX "playlist_entries_playlist" ON "playlist_entries" ("playlist");
"""
   c.executescript(schema)
   c.execute("INSERT INTO leviathan_meta (key, value) VALUES (?, ?)",
             ("db_version", DB_VERSION))
   conn.commit()
  return conn, c
 
 def all_playlists_to_mp3(self):
  for pls in os.listdir(self.playlists):
   self.playlist_to_mp3(custom_splitext(pls, ".m3u")[0])
 
 def cache_all_playlists(self):
  for pls in os.listdir(self.playlists):
   if custom_splitext(pls, ".m3u")[0] not in self.db_ignore_playlists:
    self.cache_playlist_file(pls)
 
 def cache_playlist_file(self, relpath):
  name = custom_splitext(relpath, ".m3u")[0]
  path = os.path.realpath(os.path.join(self.playlists, to_unicode(relpath)))
  if not path.startswith(os.path.realpath(self.playlists)):
   raise ValueError("The playlist's file must be within the playlist root.")
  with open(path) as f:
   lines = f.read().splitlines()
  name = to_unicode(name)
  conn, c = self._setup_db()
  if not self.crud_playlist("exists", name):
   c.execute("INSERT INTO playlists (name) VALUES (?)", [name])
  c.execute("SELECT id FROM playlists WHERE name = (?)", [name])
  pls_id = c.fetchone()[0]
  for line in lines:
   if not line.startswith("#"):
    filename = line.rsplit("\n", 1)[0]
    song_relpath = to_unicode(os.path.relpath(os.path.realpath(filename),
                                              os.path.realpath(self.library)))
    entry = self._get_song_info(song_relpath)
    if not self.crud_song("exists", song_relpath):
     c.execute("INSERT INTO songs \
                 (relpath, title, sort_title, artist, sort_artist, album, \
                  sort_album) \
                VALUES (?,?,?,?,?,?,?)", entry)
    c.execute("SELECT id FROM songs WHERE relpath = (?)", [song_relpath])
    id_ = c.fetchone()[0]
    if not self.crud_playlist_entry("exists", song_relpath, name):
     c.execute("INSERT INTO playlist_entries (song, playlist) VALUES (?,?)",
               (id_, pls_id))
    conn.commit()
  conn.commit()
  c.close()
 
 def crud_playlist(self, action="add", name="", id_=None):
  name = to_unicode(name)
  if name and not os.path.realpath(os.path.join(self.playlists, name))\
                  .startswith(os.path.realpath(self.playlists)):
   raise ValueError("The playlist's file must be within the playlist root.")
  conn, c = self._setup_db()
  if action == "list-all":
   c.execute("SELECT id, name FROM playlists ORDER BY name")
   r = c.fetchall()
   c.close()
   return r
  elif action == "exists":
   if id_ == None:
    c.execute("SELECT id FROM playlists WHERE name = (?)", [name])
   else:
    c.execute("SELECT id FROM playlists WHERE id = (?)", [id_])
   r = c.fetchone()
   c.close()
   return True if r != None else False
  elif action == "id":
   c.execute("SELECT id FROM playlists WHERE name = (?)", [name])
   r = c.fetchone()
   c.close()
   return r[0] if r != None else None
  elif action == "add":
   c.execute("INSERT INTO playlists (name) VALUES (?)", [name])
   conn.commit()
   c.execute("SELECT id FROM playlists WHERE name = (?)", [name])
   id_ = c.fetchone()[0]
   c.close()
   if os.path.exists(os.path.join(self.playlists, name + ".m3u")):
    self.cache_playlist_file(name + ".m3u")
   else:
    with open(os.path.join(self.playlists, name + ".m3u"), "w") as f:
     f.write("")
   return id_
  elif action == "list":
   if id_ == None:
    c.execute("SELECT id FROM playlists WHERE name = (?)", [name])
    id_ = c.fetchone()
    name = [name]
   else:
    id_ = [id_]
    c.execute("SELECT name FROM playlists WHERE id = (?)", [id_[0]])
    name = c.fetchone()
   if id_ == None or name == None:
    raise ValueError("The specified playlist is not in the database.")
   name, id_ = name[0], id_[0]
   c.execute("SELECT \
               relpath, title, sort_title, artist, sort_artist, album, \
               sort_album \
              FROM songs INNER JOIN playlist_entries ON \
               songs.id = playlist_entries.song AND \
               playlist_entries.playlist = ? \
              ORDER BY sort_title, sort_artist, sort_album", [id_])
   entries = [Song(*i) for i in c.fetchall()]
   return entries
  elif action == "read":
   if id_ == None:
    c.execute("SELECT name FROM playlists WHERE name = (?)", [name])
   else:
    c.execute("SELECT name FROM playlists WHERE id = (?)", [id_])
   r = c.fetchone()
   c.close()
   return r[0] if r != None else None
  elif action == "rename":
   if id_ == None:
    c.close()
    raise TypeError("You must include id_ when renaming a playlist.")
   c.execute("SELECT name FROM playlists WHERE id = (?)", [id_])
   r = c.fetchone()
   if r == None:
    c.close()
    raise ValueError("The specified playlist is not in the database.")
   old_name = r[0]
   c.execute("UPDATE playlists SET name = ? WHERE id = ?", [name, id_])
   shutil.move(os.path.join(self.playlists, old_name + ".m3u"),
               os.path.join(self.playlists, name + ".m3u"))
   if os.path.exists(os.path.join(self.playlists_mp3, old_name + ".m3u")):
    shutil.move(os.path.join(self.playlists_mp3, old_name + ".m3u"),
                os.path.join(self.playlists_mp3, name + ".m3u"))
  elif action == "delete":
   if id_ == None:
    c.execute("SELECT id FROM playlists WHERE name = (?)", [name])
    id_ = c.fetchone()
    name = [name]
   else:
    id_ = [id_]
    c.execute("SELECT name FROM playlists WHERE id = (?)", [id_[0]])
    name = c.fetchone()
   name, id_ = name[0], id_[0]
   if id_ == None or name == None:
    raise ValueError("The specified playlist is not in the database.")
   c.execute("DELETE FROM playlists WHERE id = (?)", [id_])
   c.execute("DELETE FROM playlist_entries WHERE playlist = (?)", [id_])
   if os.path.exists(os.path.join(self.playlists, name + ".m3u")):
    os.unlink(os.path.join(self.playlists, name + ".m3u"))
   if os.path.exists(os.path.join(self.playlists_mp3, name + ".m3u")):
    os.unlink(os.path.join(self.playlists_mp3, name + ".m3u"))
  conn.commit()
  c.close()
 
 def crud_playlist_entry(self, action="add", relpath="", pls=""):
  relpath, playlist = to_unicode(relpath), to_unicode(pls)
  conn, c = self._setup_db()
  c.execute("SELECT id FROM songs WHERE relpath = (?)", [relpath])
  song_id = c.fetchone()
  c.execute("SELECT id FROM playlists WHERE name = (?)", [pls])
  pls_id = c.fetchone()
  if song_id == None or pls_id == None:
   c.close()
   return False
  song_id, pls_id = song_id[0], pls_id[0]
  c.execute("SELECT id FROM playlist_entries WHERE song = ? and playlist = ?",
            [song_id, pls_id])
  r = c.fetchone()
  exists = True if r != None else False
  if action == "exists":
   c.close()
   return exists
  elif action == "add":
   if not exists:
    c.execute("INSERT INTO playlist_entries (song, playlist) VALUES (?,?)",
              (song_id, pls_id))
  elif action == "remove":
   c.execute("DELETE FROM playlist_entries WHERE song = ? AND playlist = ?",
             (song_id, pls_id))
  conn.commit()
  c.close()
  self.write_playlist(pls)
 
 def crud_song(self, action="add", relpath="", id_=None):
  relpath = to_unicode(relpath)
  if relpath and not os.path.realpath(os.path.join(self.library, relpath))\
                     .startswith(os.path.realpath(self.library)):
   raise ValueError("The song file must be within the library root.")
  conn, c = self._setup_db()
  if action == "list-all":
   c.execute("SELECT \
               id, relpath, title, sort_title, artist, sort_artist, album, \
               sort_album \
              FROM songs ORDER BY sort_title", [])
   r = c.fetchall()
   c.close()
   return [(i[0], Song(*i[1:])) for i in r]
  elif action == "exists":
   if id_ == None:
    c.execute("SELECT id FROM songs WHERE relpath = (?)", [relpath])
   else:
    c.execute("SELECT id FROM songs WHERE id = (?)", [id_])
   r = c.fetchone()
   c.close()
   return True if r != None else False
  elif action == "id":
   c.execute("SELECT id FROM songs WHERE relpath = (?)", [relpath])
   r = c.fetchone()
   c.close()
   return r[0] if r != None else None
  elif action == "playlists":
   if id_ == None:
    c.execute("SELECT id FROM songs WHERE relpath = (?)", [relpath])
    r = c.fetchone()
    if r == None:
     return False
    id_ = r
   c.execute("SELECT name FROM playlists INNER JOIN playlist_entries ON \
               playlist_entries.playlist = playlists.id AND \
               playlist_entries.song = (?) \
              ORDER BY name", [id_])
   playlists = c.fetchall()
   c.close()
   return [i[0] for i in playlists]
  elif action == "add":
   entry = self._get_song_info(relpath)
   c.execute("INSERT INTO songs \
               (relpath, title, sort_title, artist, sort_artist, album, \
                sort_album) \
              VALUES (?,?,?,?,?,?,?)", entry)
   conn.commit()
   c.execute("SELECT id FROM songs WHERE relpath = (?)", [relpath])
   id_ = c.fetchone()[0]
   c.close()
   return id_
  elif action == "read":
   if id_ == None:
    c.execute("SELECT \
                relpath, title, sort_title, artist, sort_artist, album, \
                sort_album \
               FROM songs WHERE relpath = (?)", [relpath])
   else:
    c.execute("SELECT \
                relpath, title, sort_title, artist, sort_artist, album, \
                sort_album \
               FROM songs WHERE id = (?)", [id_])
   l = c.fetchone()
   c.close()
   return Song(*l) if l != None else None
  elif action == "update":
   entry = self._get_song_info(relpath)
   if id_ == None:
    tpl = (entry.title, entry.sort_title, entry.artist, entry.sort_artist,
           entry.album, entry.sort_album, entry.relpath)
    c.execute("SELECT id FROM songs WHERE relpath = ?", [relpath])
    id_ = c.fetchone()
    if id_ == None:
     raise ValueError("The specified song does not exist.")
    id_ = id_[0]
    c.execute("UPDATE songs SET \
                title = ?, sort_title = ?, artist = ?, sort_artist = ?, \
                album = ?, sort_album = ? \
               WHERE relpath = ?", tpl)
   else:
    c.execute("SELECT id FROM songs WHERE id = ?", [id_])
    r = c.fetchone()
    if r == None:
     raise ValueError("The specified song does not exist.")
    tpl = (entry.relpath, entry.title, entry.sort_title, entry.artist,
           entry.sort_artist, entry.album, entry.sort_album, id_)
    c.execute("UPDATE songs SET \
                relpath = ?, title = ?, sort_title = ?, artist = ?, \
                sort_artist = ?, album = ?, sort_album = ? \
               WHERE id = ?", tpl)
   conn.commit()
   playlists = self.crud_song("playlists", None, id_)
  elif action == "remove":
   if id_ == None:
    c.execute("SELECT id FROM songs WHERE relpath = (?)", [relpath])
    id_ = c.fetchone()[0]
   playlists = self.crud_song("playlists", None, id_)
   c.execute("DELETE FROM songs WHERE id = (?)", [id_])
   c.execute("DELETE FROM playlist_entries WHERE song = (?)", [id_])
   conn.commit()
  if action in ("update", "remove"):
   for pls in playlists:
    self.write_playlist(pls)
  c.close()
 
 def get_album(self, artist, album, names_only=False, no_id=False):
  conn, c = self._setup_db()
  c.execute("SELECT \
              id, relpath, title, sort_title, artist, sort_artist, album, \
              sort_album \
             FROM songs WHERE artist = ? AND album = ? ORDER BY sort_title",
             [artist, album])
  r = c.fetchall()
  c.close()
  l = [(i[0], Song(*i[1:])) for i in r]
  if names_only:
   return [i[1].title for i in l]
  if no_id:
   return [i[1] for i in l]
  return l
 
 def get_albums(self, artist=None):
  conn, c = self._setup_db()
  if artist != None:
   c.execute("SELECT artist, album FROM songs WHERE artist = ? \
              GROUP BY album, artist ORDER BY sort_album", [artist])
  else:
   c.execute("SELECT artist, album FROM songs \
              GROUP BY album, artist ORDER BY sort_album", [])
  l = c.fetchall()
  c.close()
  return l
 
 def get_artist(self, artist, names_only=False, no_id=False):
  conn, c = self._setup_db()
  c.execute("SELECT \
              id, relpath, title, sort_title, artist, sort_artist, album, \
              sort_album \
             FROM songs WHERE artist = ? ORDER BY sort_title", [artist])
  r = c.fetchall()
  c.close()
  l = [(i[0], Song(*i[1:])) for i in r]
  if names_only:
   return [i[1].title for i in l]
  if no_id:
   return [i[1] for i in l]
  return l
 
 def get_artists(self):
  conn, c = self._setup_db()
  c.execute("SELECT artist FROM songs GROUP BY artist ORDER BY sort_artist")
  l = c.fetchall()
  c.close()
  return [i[0] for i in l]
 
 def get_playlist(self, playlist, names_only=False, no_id=False):
  def my_get_song_id(c, relpath):
   c.execute("SELECT id FROM songs WHERE relpath = ?", [relpath])
   r = c.fetchone()
   return r[0] if r != None else None
  if isinstance(playlist, (int, float, long)):
   l = self.crud_playlist("list", id_=playlist)
  else:
   l = self.crud_playlist("list", playlist)
  if names_only:
   return [i.title for i in l]
  if no_id:
   return l
  else:
   conn, c = self._setup_db()
   l = [(my_get_song_id(c, i.relpath), i) for i in l]
   c.close()
  return l
 
 def get_playlists(self, names_only=False):
  l = self.crud_playlist("list-all")
  if names_only:
   return [i[1] for i in l]
  return l
 
 def get_song(self, song, name_only=False, no_id=False):
  def my_get_song_id(c, relpath):
   c.execute("SELECT id FROM songs WHERE relpath = ?", [relpath])
   r = c.fetchone()
   return r[0] if r != None else None
  if isinstance(song, (int, float, long)):
   t = self.crud_song("read", id_=song)
  else:
   t = self.crud_song("read", song)
  if not t:
   return None
  if name_only:
   return t.title
  if no_id:
   return t
  else:
   if isinstance(song, (int, float, long)):
    id_ = song
   else:
    conn, c = self._setup_db()
    id_ = my_get_song_id(c, t.relpath)
    c.close()
   return (id_, t)
 
 def get_songs(self, no_id=False, names_only=False):
  l = self.crud_song("list-all")
  if names_only:
   return [i[1].title for i in l]
  if no_id:
   return [i[1] for i in l]
  return l
 
 def get_song_paths(self, name):
  name = to_unicode(name)
  conn, c = self._setup_db()
  c.execute("SELECT relpath FROM songs WHERE title = (?) ORDER BY relpath",
            [name])
  paths = c.fetchall()
  c.close()
  return [i[0] for i in paths]
 
 def move(self, src, dst):
  src, dst = to_unicode(src), to_unicode(dst)
  if not os.path.realpath(src).startswith(os.path.realpath(self.library)) or \
     not os.path.realpath(dst).startswith(os.path.realpath(self.library)):
   raise ValueError("src and dst must both be within the library root")
  src = os.path.relpath(os.path.realpath(src), os.path.realpath(self.library))
  dst = os.path.relpath(os.path.realpath(dst), os.path.realpath(self.library))
  cwd = os.getcwdu()
  os.chdir(self.library)
  if os.path.isdir(os.path.realpath(src)):
   if not os.path.exists(dst):
    os.mkdir(dst, 0755)
   if not os.path.isdir(os.path.realpath(dst)):
    raise ValueError("If src is a directory, dst must also be a directory or a"
                     " symlink to one")
   mvdir(src, dst, callback=self.update_song_path)
  else:
   if os.path.isdir(os.path.realpath(dst)):
    dst = os.path.join(dst, os.path.basename(src))
   shutil.move(src, dst)
   self.update_song_path(src, dst)
  os.chdir(cwd)
  src = os.path.join(self.library, src)
  dst = os.path.join(self.library, dst)
  for pls in os.listdir(self.playlists):
   with open(os.path.join(self.playlists, pls)) as f:
    s = to_unicode(f.read())
   s = s.replace(src, dst)
   with open(os.path.join(self.playlists, pls), "w") as f:
    f.write(s.encode("utf8"))
  if self.playlists_mp3 != "":
   self.all_playlists_to_mp3()
 
 def playlist_to_mp3(self, name):
  pls = os.path.join(self.playlists, name + ".m3u")
  mp3pls = os.path.join(self.playlists_mp3, name + ".m3u")
  if not os.path.isfile(os.path.realpath(pls)):
   raise ValueError("The playlist %s does not exist or is not a file." % pls)
  if os.path.exists(mp3pls):
   os.unlink(mp3pls)
  with open(pls, "r") as f:
   src_entries = f.read().splitlines()
  dst_entries = []
  for entry in src_entries:
   if not entry.startswith("#"):
    dst_entries.append(".".join(entry.split(".")[:-1]) + ".mp3")
   else:
    newlines.append(entry)
  with open(mp3pls, "w") as f:
   f.write("\n".join(dst_entries) + "\n")
 
 def sanitize(self, directory="", quiet=False, debug=False, level=0):
  if directory == "":
   directory = self.library
  albumart_filename = self.albumart_filename
  directory_rel = os.path.relpath(os.path.realpath(directory),
                                  os.path.realpath(self.library))
  class status:
   def __init__(self):
    self.permissions = True
    self.albumart = True
  success = status()
  try:
   ls = os.listdir(directory)
   ls.sort()
  except EnvironmentError:
   if not quiet:
    print "could not access", directory_rel
   success.permissions = False
   return False
  else:
   for i in ls:
    path = os.path.realpath(os.path.join(directory, i))
    path_rel = os.path.relpath(path, self.library)
    if os.path.isfile(path):
     try:
      os.chmod(path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
     except EnvironmentError:
      if not quiet:
       print "could not set permissions on", path_rel
      success.permissions = False
    elif os.path.isdir(path):
     try:
      os.chmod(path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
     except EnvironmentError:
      if not quiet:
       print "could not set permissions on", path_rel
      success.permissions = False
     self.sanitize(path, quiet, debug, level=level + 1)
   if level == 2:
    if albumart_filename not in ls:
     apic_status = None
     for i in ls:
      path = os.path.realpath(os.path.join(directory, i))
      path_rel = os.path.relpath(path, self.library)
      if os.path.isfile(path):
       apic_status = apic_extract(path, os.path.join(directory,
                                                     albumart_filename))
      if apic_status == True:
       if debug:
        print "made", os.path.join(directory_rel, albumart_filename)
       break
     if apic_status != True:
      if not quiet:
       print "could not find album art in", directory_rel
      success.albumart = False
  if level == 0:
   return success
 
 def to_mp3(self):
  library = self.library
  nomp3 = []
  extension_whitelist = ["." + i for i in EXTENSIONS.keys() if i != "mp3"]
  cwd = os.getcwdu()
  os.chdir(library)
  for i in os.listdir(library):
   if os.path.isdir(os.path.realpath(os.path.join(library, i))):
    for j in os.listdir(os.path.join(library, i)):
     if os.path.isdir(os.path.realpath(os.path.join(library, i, j))):
      for k in os.listdir(os.path.join(library, i, j)):
       if os.path.splitext(k)[1].lower() in extension_whitelist:
        path = os.path.join(library, i, j, k)
        if not os.path.exists(path.rsplit(".", 1)[0] + ".mp3"):
         nomp3.append(path)
     else:
      if os.path.splitext(j)[1].lower() in extension_whitelist:
       path = os.path.join(library, i, j)
       if not os.path.exists(path.rsplit(".", 1)[0] + ".mp3"):
        nomp3.append(path)
   else:
    if os.path.splitext(i)[1].lower() in extension_whitelist:
     path = os.path.join(library, i)
     if not os.path.exists(path.rsplit(".", 1)[0] + ".mp3"):
      nomp3.append(path)
  if len(nomp3) > 0:
   nomp3.sort()
   for in_file in nomp3:
    out_file = in_file.rsplit(".", 1)[0] + ".mp3"
    convert_to_mp3(in_file, out_file, self.ffmpeg, self.lame,
                   self.constant_bitrate, self.vbr_quality)
  os.chdir(cwd)
  self.all_playlists_to_mp3()
 
 def update_song_path(self, src_p, dst_p):
  id_ = self.crud_song("id", src_p)
  if id_ != None:
   self.crud_song("update", dst_p, id_)
 
 def write_playlist(self, pls):
  pls = to_unicode(pls)
  conn, c = self._setup_db()
  c.execute("SELECT id FROM playlists WHERE name = (?)", [pls])
  pls_id = c.fetchone()[0]
  c.execute("SELECT relpath FROM songs INNER JOIN playlist_entries ON \
              songs.id = playlist_entries.song AND \
              playlist_entries.playlist = ? \
             ORDER BY sort_title, sort_artist, sort_album", [pls_id])
  entries = c.fetchall()
  c.close()
  playlist = "\n".join([os.path.join(self.library, i[0]) for i in entries])
  with open(os.path.join(self.playlists, pls + ".m3u"), "w") as f:
   f.write(playlist.encode("utf8") + "\n")
  if self.playlists_mp3:
   self.playlist_to_mp3(pls)

# End of Library class

def apic_extract(mp3, jpg=None):
 try:
  tags = mutagen.mp3.Open(mp3)
 except:
  return False
 data = ""
 for i in tags:
  if i.startswith("APIC"):
   data = tags[i].data
   break
 if not data:
  return None
 if jpg != None:
  out = open(jpg, "w")
  out.write(data)
  out.close()
  return True
 return data

def convert_to_mp3(in_file, out_file, ffmpeg_path, lame_path,
                   constant_bitrate=None, vbr_quality=None):
 ffmpeg_cmd = [ffmpeg_path, "-i", in_file, "-vn", "-acodec", "pcm_s16le",
               "-f", "wav", "-"]
 lame_cmd   = [lame_path, "-m", "s", "--noreplaygain"]
 if vbr_quality != None: lame_cmd += ["-V", str(vbr_quality)]
 elif constant_bitrate: lame_cmd += ["-b", str(constant_bitrate)]
 lame_cmd += ["-", out_file]
 ffmpeg_sp = subprocess.Popen(ffmpeg_cmd, shell=False, stdout=subprocess.PIPE)
 lame_sp = subprocess.Popen(lame_cmd, shell=False, stdin=ffmpeg_sp.stdout)
 finished = False
 while not finished:
  if ffmpeg_sp.poll() not in (0, None):
   lame_sp.terminate()
   raise Exception("FFmpeg exited with code " + str(ffmpeg_sp.returncode))
  if lame_sp.poll() not in (0, None):
   ffmpeg_sp.terminate()
   raise Exception("LAME exited with code " + str(lame_sp.returncode))
  if ffmpeg_sp.poll() == 0 and lame_sp.poll() == 0:
   finished = True
 in_file_ext = in_file.rsplit(".", 1)[1].lower()
 if in_file_ext in EXTENSIONS:
  in_tags  = mutagen.File(in_file, easy=True)
  out_tags = mutagen.File(out_file, easy=True)
  if None not in (in_tags, out_tags):
   for i in in_tags:
    if i in EasyID3.valid_keys:
     out_tags[i] = in_tags[i]
   out_tags.save()

def custom_splitext(path, match=None):
 split = os.path.splitext(path)
 if match == None or split[1] == match:
  return split
 else:
  return (path, "")

def get_format(ext):
 ext = ext.lower().lstrip(".")
 if ext in EXTENSIONS:
  return EXTENSIONS[ext]
 return None

def main(argv):
 commands = ["sanitize", "to-mp3", "playlists-to-mp3", "cache", "song",
             "playlist", "pls", "move", "mv", "help", "-h", "--help"]
 usage = """Usage: %s command [arguments]

Commands:        Arguments:
cache
 Adds all songs that are in playlists to a SQLite database.
move|mv          src dst
 Moves a song in the filesystem and updates the database and playlists to match.
playlist|pls     add|delete|ls|write playlist-name
 Creates, deletes, lists, or writes a playlist.
playlist|pls     rename old-name new-name
 Renames a playlist.
playlist|pls     ls|write-all
 Lists all playlists or writes all playlists to their respective files.
playlist|pls     add|remove song-path playlist-name [playlist-name]...
 Adds or removes a song from one or more playlists.
playlists-to-mp3
 Creates MP3-only copies of all playlists.
sanitize
 Fixes permissions and makes sure all albums with artwork have an albumart.jpg.
song             add|update|remove song-path
 Adds, updates, or removes a song in the database (DOES NOT affect the file).
song             path[s] song-name
 Prints all relative (to the library root) paths of a song in the database.
to-mp3
 Makes sure MP3 versions of all songs and playlists exist.
help|-h|--help
 Shows this usage information and exits.\
""" % argv[0]
 
 if len(argv) < 2:
  print usage
  return 2
 
 if argv[1] == "-c":
  if len(argv) < 3:
   print "Please specify a configuration file or omit -c."
   return 2
  conf_file = argv.pop(2)
  argv.pop(1)
 elif argv[1].startswith("--config-file="):
  conf_file = argv.pop(1).split("=", 1)[1]
  if conf_file == "":
   print "Please specify a configuration file or omit --config-file."
   return 2
 else:
  conf_file = os.path.expanduser("~/.leviathan.yaml")
 
 cmd = argv[1]
 
 if cmd not in commands:
  print "invalid command:", cmd
  return 2
 
 if cmd in ("help", "-h", "--help"):
  print usage
  return 0
 
 try:
  library = Library(conf_file)
 except EnvironmentError as exc:
  print "error:", exc
  return 1
  
 if cmd == "cache":
  library.cache_all_playlists()
 elif cmd in ("move", "mv"):
  if len(argv) < 4:
   print "Usage: %s move|mv src dst" % sys.argv[0], cmd
   return 2
  try:
   library.move(argv[2], argv[3])
  except UnicodeError:
   traceback.print_exc()
  except (EnvironmentError, ValueError) as exc:
   print exc
 elif cmd in ("playlist", "pls"):
  if (len(argv)  < 3) or \
     (len(argv) == 3 and argv[2] not in ("write-all", "ls")) or \
     (len(argv) == 4 and argv[2] not in ("add", "delete", "ls", "write")) or \
     (len(argv) != 5 and argv[2] == "rename" ) or \
     (len(argv)  > 4 and argv[2] not in ("add", "rename", "remove")):
   print "Usage: %s playlist|pls add|delete|ls|write playlist-name" % argv[0]
   print "   or: %s playlist|pls rename old-name new-name" % argv[0]
   print "   or: %s playlist|pls ls|write-all" % argv[0]
   print "   or: %s playlist|pls add|remove song-path playlist-name [playlist-name]..." % argv[0], argv[1]
   return 2
  elif len(argv) == 4 or argv[2] == "rename":
   pls = argv[3]
   if "/" in pls:
    pls = os.path.relpath(pls, library.playlists)
   pls = custom_splitext(pls, ".m3u")[0]
   if argv[2] == "delete":
    r = yes_no_prompt("Are you sure you want to delete the playlist %s?" % pls)
    if not r:
     return 1
   if argv[2] == "rename":
    pls2 = argv[4]
    if "/" in pls2:
     pls2 = os.path.relpath(pls2, library.playlists)
    pls2 = custom_splitext(pls2, ".m3u")[0]
    id_ = library.crud_playlist("id", pls)
    library.crud_playlist(argv[2], pls2, id_)
   elif argv[2] == "write":
    library.write_playlist(pls)
   elif argv[2] == "ls":
    entries = library.crud_playlist("list", pls)
    for i in entries:
     print i.title.encode("utf8"),
     if i.artist or i.album:
      print "(%s)" % ", ".join([j for j in (i.artist, i.album) if j]).encode("utf8")
   else:
    library.crud_playlist(argv[2], pls)
  elif argv[2] in ("ls", "write-all"):
   playlists = library.crud_playlist("list-all")
   if argv[2] == "ls":
    print ", ".join([i[1] for i in playlists]).encode("utf8")
   else:
    for pls in playlists:
     if pls not in library.db_ignore_playlists:
      library.write_playlist(pls[1])
  else:
   playlists = argv[4:]
   song = os.path.relpath(os.path.realpath(argv[3]),
                          os.path.realpath(library.library))
   if argv[2] == "remove":
    r = yes_no_prompt("Are you sure you want to remove %s from the"
                      " playlist(s)?" % argv[3])
    if not r:
     return 1
   if not library.crud_song("exists", song):
    library.crud_song("add", song)
   all_playlists = [i[1] for i in library.crud_playlist("list-all")]
   for pls in playlists:
    if "/" in pls:
     pls = os.path.relpath(pls, library.playlists)
    pls = custom_splitext(pls, ".m3u")[0]
    if pls not in all_playlists:
     print "warning: ignoring playlist %s because it does not exist." % pls
     continue
    library.crud_playlist_entry(argv[2], song, pls)
 elif cmd == "playlists-to-mp3":
  library.all_playlists_to_mp3()
 elif cmd == "sanitize":
  quiet = ("-q" in argv or "--quiet" in argv)
  debug = ("-d" in argv or "--debug" in argv)
  success = library.sanitize(quiet=quiet, debug=debug)
  if success.albumart == False and not quiet:
   print "* not all album directories have album art *"
  if success.permissions == False:
   print "* not all files and directories could be sanitized *"
 elif cmd == "song":
  if (len(argv)  < 4) or \
     (len(argv) == 4 and argv[2] not in ("add", "update", "remove",
                                         "path", "paths")) or \
     (len(argv)  > 4 and argv[2] not in ("path", "paths")):
   print "Usage: %s song add|update|remove song-path" % argv[0]
   print "   or: %s song path[s] song-name" % argv[0]
   return 2
  song = os.path.relpath(os.path.realpath(argv[3]),
                         os.path.realpath(library.library))
  if argv[2] == "remove":
   r = yes_no_prompt("Are you sure you want to remove the song %s from the"
                     " database?" % song)
   if not r:
    return 1
  if argv[2] == "path" or argv[2] == "paths":
   name = " ".join(argv[3:])
   if name == "":
    print "Please specify the name of a song."
    return 2
   for i in library.get_song_paths(name):
    print i
   return 0
  library.crud_song(argv[2], song)
 elif cmd == "to-mp3":
  library.to_mp3()
 return 0

def mvdir(src, dst, callback=None, _first_level=True):
 if not os.path.exists(dst):
  os.mkdir(dst, 0755)
 if not os.path.isdir(os.path.realpath(src)):
  raise ValueError, "%s is not a directory" % src
 if not os.path.isdir(os.path.realpath(dst)):
  raise ValueError, "%s is not a directory" % dst
 for i in os.listdir(src):
  src_p, dst_p = os.path.join(src, i), os.path.join(dst, i)
  if os.path.isdir(os.path.realpath(src_p)):
   mvdir(src_p, dst_p, callback, False)
  else:
   shutil.move(src_p, dst_p)
  if callable(callback):
   callback(src_p, dst_p)
 os.rmdir(src)
 if _first_level and callback != None and not callable(callback):
  raise TypeError, "callback is not callable"

def setattrs(d, _cls = None):
 setattrs_class = _cls
 if _cls == None:
  class setattrs_class: pass
 for i in d:
  if isinstance(d[i], dict):
   setattr(setattrs_class, i, setattrs(d[i]))
  else:
   setattr(setattrs_class, i, d[i])
 if _cls == None:
  return setattrs_class

def sort_value(s):
 s = to_unicode(strip_latin_diacritics(s)).lower()
 if s.startswith("the "):
  s = s.replace("the ", "", 1) + ", the"
 elif s.startswith("an "):
  s = s.replace("an ", "", 1) + ", an"
 elif s.startswith("a "):
  s = s.replace("a ", "", 1) + ", a"
 return s

# replace Latin letters with diacritical marks with the same letters without
# diacritics, preserving case
def strip_latin_diacritics(string):
 ret = string
 latin_diacritics = {
  "A": u"ÁÀĂẮẰẴẲÂẤẦẪẨǍÅǺÄǞÃȦǠĄĀẢȀȂẠẶẬḀȺǼǢ",
  "B": u"ḂḄḆɃƁƂ",
  "C": u"ĆĈČĊÇḈȻƇ",
  "D": u"ĎḊḐḌḒḎĐƉƊƋ",
  "E": u"ÉÈĔÊẾỀỄỂĚËẼĖȨḜĘĒḖḔẺȄȆẸỆḘḚɆ",
  "F": u"ḞƑ",
  "G": u"ǴĞĜǦĠĢḠǤƓ",
  "H": u"ĤȞḦḢḨḤḪH̱ĦⱧ",
  "I": u"ÍÌĬÎǏÏḮĨİĮĪỈȈȊỊḬIƗᵻ",
  "J": u"ĴJ̌Ɉ",
  "K": u"ḰǨĶḲḴꝄꝂꝀƘⱩ",
  "L": u"ĹĽĻḶḸḼḺŁŁĿȽⱠⱢꝈꝆ",
  "M": u"ḾṀṂ",
  "N": u"ŃǸŇÑṄŅṆṊṈƝȠN",
  "O": u"ÓÒŎÔỐỒỖỔǑÖȪŐÕṌṎȬȮȰØǾǪǬŌṒṐỎȌȎƠỚỜỠỞỢỌỘƟꝊꝌ",
  "P": u"ṔṖⱣꝐƤꝒꝔP",
  "Q": u"ꝘɊ",
  "R": u"ŔŘṘŖȐȒṚṜṞɌꞂⱤ",
  "S": u"ŚṤŜŠṦṠŞṢṨȘSꞄ",
  "SS": u"ẞ",
  "T": u"ŤTṪŢṬȚṰṮŦȾƬƮ",
  "U": u"ÚÙŬÛǓŮÜǗǛǙǕŰŨṸŲŪṺỦȔȖƯỨỪỮỬỰỤṲṶṴɄᵾ",
  "V": u"ṼṾƲ",
  "W": u"ẂẀŴW̊ẄẆẈꝠ",
  "X": u"ẌẊ",
  "Y": u"ÝỲŶY̊ŸỸẎȲỶỴʏɎƳ",
  "Z": u"ŹẐŽŻẒẔƵȤⱫǮꝢ",
  "a": u"áàăắằẵẳâấầẫẩǎåǻäǟãȧǡąāảȁȃạặậḁⱥᶏǽǣᶐ",
  "b": u"ḃḅḇƀᵬᶀɓƃ",
  "c": u"ćĉčċçḉȼƈɕ",
  "d": u"ďḋḑḍḓḏđᵭᶁɖɗᶑƌȡ",
  "e": u"éèĕêếềễểěëẽėȩḝęēḗḕẻȅȇẹệḙḛɇᶒᶕɚᶓᶔɝ",
  "f": u"ḟᵮᶂƒ",
  "g": u"ǵğĝǧġģḡǥᶃɠ",
  "h": u"ĥȟḧḣḩḥḫẖħⱨ",
  "i": u"íìĭîǐïḯĩiįīỉȉȋịḭıɨᶖ",
  "j": u"ĵǰȷɉʝɟʄ",
  "k": u"ḱǩķḳḵꝅꝃꝁᶄƙⱪ",
  "l": u"ĺľļḷḹḽḻłł̣ŀƚⱡɫꝉꝇɬᶅɭȴ",
  "m": u"ḿṁṃᵯᶆɱ",
  "n": u"ńǹňñṅņṇṋṉᵰɲƞᶇɳȵn̈",
  "o": u"óòŏôốồỗổǒöȫőõṍṏȭȯȱøǿǫǭōṓṑỏȍȏơớờỡởợọộɵꝋꝍ",
  "p": u"ṕṗᵽꝑᶈƥꝓꝕp̃",
  "q": u"ʠꝙɋ",
  "r": u"ŕřṙŗȑȓṛṝṟɍᵲᶉɼꞃɽɾᵳ",
  "s": u"śṥŝšṧṡẛşṣṩșᵴᶊʂȿs̩ꞅᶋᶘ",
  "ss": u"ß",
  "t": u"ťẗṫţṭțṱṯŧⱦᵵƫƭʈȶ",
  "u": u"úùŭûǔůüǘǜǚǖűũṹųūṻủȕȗưứừữửựụṳṷṵʉᶙᵿ",
  "v": u"ṽṿᶌʋⱴ",
  "w": u"ẃẁŵẘẅẇẉꝡ",
  "x": u"ẍẋᶍ",
  "y": u"ýỳŷẙÿỹẏȳỷỵɏƴ",
  "z": u"źẑžżẓẕƶᵶᶎȥʐʑɀⱬǯᶚƺꝣ"
 }
 for letter in latin_diacritics:
  for i in latin_diacritics[letter]:
   ret = ret.replace(i, letter)
 return ret

def test_settings(conf_file=None):
 if not conf_file:
  conf_file = os.path.expanduser("~/.leviathan.yaml")
 library = Library(conf_file)
 return config, library

def to_unicode(s, encoding="utf8"):
 if isinstance(s, (str, buffer)):
  return unicode(s, encoding)
 return s

def yes_no_prompt(prompt="Are you sure?"):
 r = raw_input("%s (yes/[no]) " % prompt)
 while r not in ("yes", "no", ""):
  r = raw_input('Please type "yes" or "no": ')
 return True if r == "yes" else False

if __name__ == "__main__":
 try:
  exitcode = main(sys.argv)
  sys.exit(exitcode)
 except (KeyboardInterrupt, SystemExit):
  pass
 except UnicodeError:
  traceback.print_exc()
 #except (TypeError, ValueError) as exc:
 # print "error:", exc
 # sys.exit(2)
