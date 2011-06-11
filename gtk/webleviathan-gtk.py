#!/usr/bin/env python

APP_NAME    = "Leviathan Music Player"
APP_ID      = "webleviathan-gtk"
APP_VERSION = "1.0"
APP_ICON    = "webleviathan-gtk"
APP_URL_KEY = "/apps/webleviathan-gtk/url"

import os
import platform
import sys

if platform.system() == "Linux":
 sys.argv[0] = APP_ID

import gconf
import gtk
import urlparse
import webkit

def check_url(url):
 url = urlparse.urlsplit(url)
 if url.scheme not in ("http", "https", "spdy"):
  return False
 if not url.netloc:
  return False
 return True

def close_callback(window, data):
 window.hide()
 sys.exit()

def error_dlg(msg, extra=None, type=gtk.MESSAGE_WARNING,
              menu_item_sensitivity=True):
 dlg = gtk.MessageDialog(None, gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                         type, gtk.BUTTONS_OK, msg)
 set_icon(dlg)
 dlg.set_title(APP_NAME)
 if extra:
  dlg.set_size_request(480, -1)
  sw = gadd(gtk.ScrolledWindow(), dlg.vbox.get_children()[0].get_children()[1])
  sw.set_size_request(-1, 160)
  tv = gadd(gtk.TextView(), sw)
  tv.set_editable(False)
  tv.set_wrap_mode(gtk.WRAP_WORD)
  tb = tv.get_buffer()
  tb.set_text(extra)
  tb.apply_tag(tb.create_tag(font="Monospace 10"), tb.get_start_iter(),
               tb.get_end_iter())
 dlg.action_area.get_children()[0].grab_default()
 dlg.action_area.get_children()[0].grab_focus()
 dlg.run()
 dlg.destroy()

def gadd(child, parent, **kwargs):
 try:
  parent.pack_start(child, **kwargs)
 except AttributeError:
  try:
   parent.append(child)
  except AttributeError:
   parent.add(child)
 child.show()
 return child

def get_url():
 c = gconf.Client()
 return c.get_string(APP_URL_KEY)

def gframe(label=None, parent=None, spacing=0, **kwargs):
 f = gtk.Frame(label)
 vbox0 = gadd(gtk.VBox(), f)
 hbox = gadd(gtk.HBox(spacing=spacing), vbox0, padding=spacing)
 vbox1 = gadd(gtk.VBox(spacing=spacing), hbox, padding=spacing)
 if parent:
  gadd(f, parent, **kwargs)
 return f, vbox1

def run_set_url_dialog():
 SP = 5
 url = get_url() or ""
 dialog = gtk.Dialog(APP_NAME, None,
                     gtk.DIALOG_DESTROY_WITH_PARENT,
                     (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                      gtk.STOCK_OK, gtk.RESPONSE_OK))
 set_icon(dialog)
 dialog.set_resizable(False)
 dialog.set_size_request(320, -1)
 hbox = gadd(gtk.HBox(spacing=SP), dialog.vbox, padding=SP)
 vbox = gadd(gtk.VBox(spacing=SP), hbox, padding=SP)
 gadd(gtk.Label("Please enter the URL for your copy of the"), vbox)
 gadd(gtk.Label(APP_NAME + "."), vbox)
 url_box = gadd(gtk.Entry(), vbox, padding=SP)
 url_box.set_text(url)
 def cancel_callback(btn=None):
  dialog.hide()
  dialog.destroy()
 def dlg_close_callback(window, data):
  cancel_callback()
  return False
 def check():
  if not check_url(url_box.get_text() or ""):
   error_dlg("Please enter a valid URL.")
   return False
  return True
 def ok_callback(btn):
  if check():
   set_url(url_box.get_text())
   dialog.hide()
   dialog.destroy()
 dialog.action_area.get_children()[0].connect("clicked", ok_callback)
 dialog.action_area.get_children()[1].connect("clicked", cancel_callback)
 dialog.connect("delete-event", dlg_close_callback)
 dialog.show()
 while dialog.get_visible():
  gtk.main_iteration(False)
 if check_url(get_url() or ""):
  return True
 return False

def set_icon(window):
 icon_dir = os.path.join(os.path.dirname(sys.argv[0]), "icon")
 sizes = ["16.png", "32.png", "48.png", "scalable.svg"]
 use_files = False
 if os.path.isdir(os.path.realpath(icon_dir)):
  use_files = True
  for i in sizes:
   if not os.path.isfile(os.path.realpath(os.path.join(icon_dir, i))):
    use_files = False
    break
 if use_files:
  icons = [gtk.gdk.pixbuf_new_from_file(os.path.join(icon_dir, i))
           for i in sizes]
  window.set_icon_list(*icons)
 else:
  window.set_icon_name(APP_ICON)

def set_url(url):
 c = gconf.Client()
 c.set_string(APP_URL_KEY, url)

try:
 url = get_url()
 if not url or not check_url(url):
  run_set_url_dialog()
  url = get_url()
  if not url:
   sys.exit(1)
 elif "-s" in sys.argv or "--set-url" in sys.argv:
  run_set_url_dialog()
  sys.exit(0)
 
 w = gtk.Window(gtk.WINDOW_TOPLEVEL)
 w.set_title(APP_NAME)
 w.set_role("mainWindow")
 set_icon(w)
 w.set_size_request(1, 1)
 w.resize(800, 500)
 w.connect("delete-event", close_callback)
 
 s = gtk.ScrolledWindow()
 wv = webkit.WebView()
 wv.open(url)
 s.add(wv)
 w.add(s)
 
 try:
  import gnome
  import gnome.ui
  gnome.init(APP_ID, APP_VERSION)
  client = gnome.ui.master_client()
  client.connect("die", gtk.main_quit)
 except ImportError:
  pass
 
 while gtk.events_pending():
  gtk.main_iteration()
 
 w.show_all() 
 gtk.main()
except KeyboardInterrupt:
 print "bnay"
 sys.exit()
