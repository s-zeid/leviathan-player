Leviathan Music Player
======================

A Web-based music player based on the Leviathan music library manager.

Copyright (C) 2008-2011 Scott Zeid  
[http://me.srwz.us/leviathan/player](http://me.srwz.us/leviathan/player)

Leviathan Music Player is a Web-based music player.  It uses the Leviathan
music library manager to find your songs and playlists.  Both the music player
and the library manager use configuration files to store their settings, and
these files must be edited manually.

Requirements
------------
 *  On the server:
     * Python 2.6 or 2.7
     * Mutagen
     * FFmpeg (proprietary codecs recommended)
     * LAME
     * Bottle
     * pylast
     * mod-wsgi (for Apache only)
    
    To install these packages on Ubuntu, run:
    
        $ sudo apt-get install python python-mutagen python-setuptools \
          ffmpeg libavcodec-extra-\* libavdevice-extra-\* libavfilter-extra-\* \
          libavformat-extra-\* libavutil-extra-\* libpostproc-extra-\* \
          libswscale-extra-\* lame
        $ sudo easy_install -U bottle pylast
    
    If you're using Apache, also run:
    
        $ sudo apt-get install libapache2-mod-wsgi
    
 *  On the client:
      * A standards-compliant Web browser that supports HTML5/CSS3/JavaScript.
        Firefox 4+, Google Chrome, Safari, and Opera 10.5+ should work.  IE9
        might work.  IE7 works but is very buggy.  IE6 and earlier will
        probably NOT work.
      * Adobe Flash Player 9.0+

Installation
------------
See the `INSTALL` file for installation instructions.

Configuration
-------------
Leviathan Music Player uses two configuration files:

 * `leviathan/leviathan.yaml`
   
   This contains settings for the music manager.  Here is where you enter the
   paths to your music collection, your playlist folders, FFmpeg, and LAME,
   as well as the quality settings for MP3 encoding.  Also specify what you
   want album art files to be called (use albumart.jpg if you intend to sync
   your music collection with an Android device).
   
   If you already have another copy of Leviathan Music Manager already set up,
   you can change the `leviathan.yaml` setting in `webleviathan.yaml` to point to
   the path of the configuration file you already have.
   
 * `webleviathan.yaml`
   
   This contains settings for the music player.  You can:
   
   * Set whether repeat, shuffle, and Last.fm scrobbling are on or off by
     default.
   * Enter your Last.fm username and password if you wish to scrobble your
     music.  If you do this, make sure nobody can access this file except you.
   * Choose a color theme for the music player.  Color themes are contained
     in the `themes` directory.  Enter the name of the theme you want to use
     without the .yaml extension.

Artwork Cache
-------------
Cover art is cached under the `artwork-cache/library/` directory.  All sizes
that have ever been displayed in the music player are stored here.  However,
most of the files here are 16x16 pixels (shown in the lists) and 92x92 pixels
(shown in the toolbar).  In my testing, with a library of around 700 songs and
heavy use over the course of three months, the size of these files is only
around 24 megabytes.

Usage
-----
After installing Leviathan Music Player, use your Web browser to go to the URL
that you set up the player on.

The top of the screen contains a toolbar which displays the title, artist,
album, and cover art of the currently playing song, and it also has playback
controls.  The section underneath the toolbar is split into two parts:  the
library and the now playing section.

The library shows the artists, albums, playlists, and songs in your music
collection and lets you drill down to find the song you want to listen to.
Clicking on a song in the library section will replace the now playing section
with all of the songs in the artist, album, playlist, or songs list that you
clicked in.  To just add a song to the now playing section, click on the plus
sign next to the song.

The now playing section shows all of the songs that may be played after the
current song finishes.  Clicking on a song here will cause that song to be
played with no changes to the list.  Clicking on the X next to a song will
remove it from the list.  The next song in the list will be played, or if
shuffle is enabled, a random song will be chosen.  Clicking on Clear at the
top of the list will remove all songs from the Now Playing list and stop
playback.
