# -*- coding: utf-8 -*-

# Jug of Punch
# Extensions to the Bottle framework.
# 
# Copyright (C) 2010-2012 Scott Zeid
# http://code.srwz.us/jug-of-punch
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

"""Extensions to the Bottle framework.

This module contains everything that the bottle module contains, as well as \
extensions that are intended to aid in Web app development, especially for \
developers coming from PHP and those who need to easily define global \
variables in their templates.

"""

import cgi
import functools
import htmlentitydefs
import optparse
import os
import re
import sys
import time
import urllib
import urlparse

from bottle import *
import yaml

class config:
 """Stores configuration values for the current application.

Default values:
 development  - settings for development mode
 development.host = "127.0.0.1"  - default host name to bind to
 development.port = 8080  - default port number to bind to
 development.debug = True  - whether to use debug mode
 template  - template settings
 template.defaults = {}  - default template variables
 template.engine = SimpleTemplate  - default Bottle template engine to use
 template.title_format = "%(page)s - %(site)s"  - HTML title format

"""
 class development:
  host = "127.0.0.1"
  port = 8080
  debug = True
 class template:
  defaults = dict()
  engine = SimpleTemplate
  title_format = "%(page)s - %(site)s"
 
 _default_config_file = "config.yaml"
 
 @classmethod
 def __init__(self, config_file=True, root=None):
  if not root:
   root = os.path.abspath(sys.argv[0])
  if os.path.isdir(os.path.realpath(os.path.abspath(root))):
   self.root = os.path.abspath(root)
  else:
   self.root = os.path.dirname(os.path.abspath(root))
  self._root = self._original_root = self.root
  os.chdir(self.root)
  if config_file == True:
   config_file = self._default_config_file
  if config_file and os.path.exists(config_file):
   self.load(config_file)
 
 @classmethod
 def load(self, fname=_default_config_file):
  self._dict = load_yaml_file(abspath(fname))
  setattrs(self._dict, self)
  if self.root != self._root:
   self._root = self.root
   os.chdir(self.root)
  debug(False)

class JugOfPunchMiddleware(object):
 """Middleware that does some stuff specific to Jug of Punch.

Currently, it handles the following WSGI environment variables and HTTP \
headers:

FORCE_HTTPS / X-JugOfPunch-ForceHTTPS
  Forces the URL scheme to "https" and sets "HTTP_X_FORWARDED_SSL" to "on".
FORCE_SCRIPT_NAME / X-JugOfPunch-ForceScriptName
  Forces the script name (the part leading up to the root of the app) to the
  specified value.  Useful in conjunction with REMOVE_PATH_PREFIX.
REMOVE_PATH_PREFIX / X-JugOfPunch-RemovePathPrefix
  Removes the specified prefix (e.g. /some/thing) from the request's path.

If both the environment variable and the header for the same setting are set, \
then the environment variable takes precedence.

"""
 def __init__(self, app):
  self.app = app
 def __call__(self, environ, start_response):
  self.fix_https(environ)
  self.fix_path_info(environ)
  self.fix_script_name(environ)
  return self.app(environ, start_response)
 def fix_https(self, environ):
  force_https = False
  if "FORCE_HTTPS" in environ:
   force_https = environ.get("FORCE_HTTPS", "") == "True"
   del environ["FORCE_HTTPS"]
  elif "HTTP_X_JUGOFPUNCH_FORCEHTTPS" in environ:
   force_https = environ.get("HTTP_X_JUGOFPUNCH_FORCEHTTPS", "") == "True"
   del environ["HTTP_X_JUGOFPUNCH_FORCEHTTPS"]
  if force_https:
   environ["HTTP_X_FORWARDED_SSL"] = "on"
   environ["wsgi.url_scheme"] = "https"
 def fix_path_info(self, environ):
  prefix = None
  if "REMOVE_PATH_PREFIX" in environ:
   prefix = environ.get("REMOVE_PATH_PREFIX", "").rstrip("/")
   del environ["REMOVE_PATH_PREFIX"]
  elif "HTTP_X_JUGOFPUNCH_REMOVEPATHPREFIX" in environ:
   prefix = environ.get("HTTP_X_JUGOFPUNCH_REMOVEPATHPREFIX", "").rstrip("/")
   del environ["HTTP_X_JUGOFPUNCH_REMOVEPATHPREFIX"]
  if prefix and environ["PATH_INFO"].startswith(prefix):
   environ["PATH_INFO"] = environ["PATH_INFO"].split(prefix, 1)[-1]
 def fix_script_name(self, environ):
  script_name = None
  if "FORCE_SCRIPT_NAME" in environ:
   script_name = environ.get("FORCE_SCRIPT_NAME", "").rstrip("/")
   del environ["FORCE_SCRIPT_NAME"]
  elif "HTTP_X_JUGOFPUNCH_FORCESCRIPTNAME" in environ:
   script_name = (environ.get("HTTP_X_JUGOFPUNCH_FORCESCRIPTNAME", "")
                  .rstrip("/"))
   del environ["HTTP_X_JUGOFPUNCH_FORCESCRIPTNAME"]
  if script_name:
   environ["SCRIPT_NAME"] = script_name
   environ["SCRIPT_NAME_FORCED"] = "True"
  else:
   environ["SCRIPT_NAME_FORCED"] = "False"

def abspath(path):
 """Returns the absolute path for a given subpath, relative to config.root."""
 return os.path.join(config.root, path)

def args():
 """Returns a list of path components for the current request.

The first element is always the script name.

"""
 path = request.path.split("/")
 path[0] = script()
 return path

@route("/favicon.ico")
@route("/favicon.png")
def favicon():
 """Returns the static/favicon.ico or static/favicon.png file.

Bound to the routes "/favicon.ico" and "/favicon.png".

"""
 if request.path == "/favicon.ico":
  return static_file("favicon.ico", os.path.join(config.root, "static"))
 elif request.path == "/favicon.png":
  return static_file("favicon.png", os.path.join(config.root, "static"))

def generate_tplvars(template_adapter=None, **kwargs):
 """Returns a dictionary of template variables.

Set no_entities to False if you do not want special characters other than \
", &, <, and > to be converted to HTML entities.

If any value appears to be a function or method, it is called with no \
arguments and the return value is used instead of the callable itself.

The tplvars key is useful with the %rebase SimpleTemplate keyword.

The dictionary is populated in the following order:
 - The contents of config.template.defaults
 - The keyword arguments passed to this function.
 - handler - the function name handling the current request
 - page_title - according to config.template.title_format
 - page_name - as given in kwargs or None if not given
 - args - the value returned by args()
 - device - the mobile device name if this request appears to be from a
            mobile device
 - mobile - whether this request appears to be from a mobile device
 - root_path
 - root_url
 - site_name - config.name; can be overridden in defaults or kwargs
 - title_format - config.template.title_format
 - ua - the user agent for the current request
 - wii - whether this request appears to be from a Wii
 - no_entities - whether special characters not in ["&<>] are converted
                 to HTML entities
 - tplvars - the same dictionary that is returned by this function.

"""
 if not template_adapter:
  template_adapter = config.template.engine
 tplvars = getattr(config.template, "defaults", {}).copy()
 tplvars.update(kwargs)
 site_name = tplvars.get("site_name", config.name)
 if "handler" not in tplvars:
  tplvars["handler"] = handler()
 if "page_title" not in tplvars:
  if "page_name" in tplvars:
   tplvars["page_title"] = (config.template.title_format
                            % dict(page=tplvars["page_name"], site=site_name))
  else:
   tplvars["page_name"] = None
   tplvars["page_title"] = site_name
 tplvars["args"] = args()
 tplvars["device"] = is_mobile(return_device=True)
 tplvars["mobile"] = is_mobile()
 tplvars["root_path"] = root_path()
 tplvars["root_url"] = root_url()
 tplvars["site_name"] = site_name
 tplvars["title_format"] = config.template.title_format
 tplvars["ua"] = request.headers.get("User-Agent", "")
 tplvars["wii"] = "wii" in request.headers.get("User-Agent", "").lower() or "forcewii" in request.GET
 if "no_entities" not in tplvars or tplvars["no_entities"] != True:
  tplvars["no_entities"] = False
  tplvars = htmlentities(tplvars)
 for i in tplvars:
  if callable(tplvars[i]):
   try:
    tplvars[i] = tplvars[i]()
   except:
    tplvars[i] = tplvars[i]
 tplvars["tplvars"] = tplvars
 return tplvars

# from Bottle
mako_tplvars = functools.partial(generate_tplvars, template_adapter=MakoTemplate)
cheetah_tplvars = functools.partial(generate_tplvars, template_adapter=CheetahTemplate)
jinja2_tplvars = functools.partial(generate_tplvars, template_adapter=Jinja2Template)

def handler():
 """Returns the name of the function that is handling the current request, or \
"error" if the current request resulted in an HTTP error, or if the function \
cannot be found."""
 # TODO:  Update this function when Bottle 0.10 code gets pushed and "the
 #        semantics [of Bottle.match] change"
 match = None
 try:
  # Bottle 0.9
  match = app().match(request.environ)
  try:
   # Bottle 0.10+
   match = (match[0].callback,)
  except AttributeError:
   pass
 except HTTPError:
  return "error"
 except AttributeError:
  try:
   # Bottle 0.8
   match = app().match_url(request.path)
  except HTTPError:
   return "error"
 return match[0].func_name if match else "error"

def htmlentities(text, exclude="\"&<>", table=htmlentitydefs.codepoint2name):
 """Converts all special characters except ", &, <, and > to HTML entities.

Lists and dictionaries are handled recursively.

The exclude argument is a list of characters to not process.  It defaults to \
excluding quotation marks, ampersands, and angle brackets.  Keep this in mind \
if you are converting something from PHP.

The table argument specifies an alternate table to use for conversion.  It \
should be of the format {ord(character): "entity-name", ...}; e.g. {34: "quot"}.

"""
 if isinstance(text, list):
  out = []
  for i in text:
   out.append(htmlentities(i, exclude, table))
 elif isinstance(text, dict):
  out = {}
  for i in text:
   out[i] = htmlentities(text[i], exclude, table)
 elif isinstance(text, basestring):
  if isinstance(text, unicode):
   out = u""
  else:
   out = ""
  for i in text:
   if ord(i) in table and i not in exclude:
    out += "&" + table.get(ord(i)) + ";"
   else:
    out += i
 else:
  out = text
 return out

def htmlspecialchars(text):
 """Converts all HTML reserved characters (", &, <, and >) to HTML entities.

Lists and dictionaries are handled recursively.

"""
 return htmlentities(text, exclude="",
                     table={34: "quot", 38: "amp", 60: "lt", 62: "gt"})

@route("/images/:filename#[a-zA-Z0-9\-_\.\/]+#")
def images(filename):
 """Returns a given file located under the "images" directory.

This is bound to the route "/images/:filename#[a-zA-Z0-9\-_\.\/]+#".

"""
 if ".." not in filename.split("/"):
  return static_file(filename, os.path.join(config.root, "images"))
 else:
  abort(403)

def is_mobile(headers, GET, return_device=False):
 """Attempts to determine whether the current request is a mobile device based \
on the user agent string."""
 if callable(headers):
  headers = headers()
 if callable(GET):
  GET = GET()
 # config
 ua = headers.get("User-Agent", "").lower()
 nomobile = False
 forcemobile = False
 forcedevice = None
 GET_mobile = GET.get("mobile")
 GET_device = GET.get("device")
 if GET.get("nomobile") != None or GET.get("!mobile") != None:
  nomobile = True
 elif GET_mobile != None:
  if GET_mobile.lower() != "ipad":
   forcemobile = True
  forcedevice = GET.get("mobile").lower()
  if forcedevice == "":
   forcedevice = "unknown"
 if GET_device != None and GET_device != "":
  if GET_device.lower() != "ipad":
   forcemobile = True
   nomobile = False
  forcedevice = GET_device.lower()
 # is mobile device?
 if (("iphone" in ua or "ipod" in ua or "android" in ua or "webos" in ua) and nomobile == False) or forcemobile == True:
  mobile = True
 else:
  mobile = False
 if return_device == True:
  # which mobile device
  device = "unknown"
  if "iphone" in ua or "ipod" in ua:
   device = "apple"
  elif "ipad" in ua:
   device = "ipad"
  elif "android" in ua:
   device = "android"
  elif "webos" in ua:
   device = "webos"
  if forcedevice != "" and forcedevice != None:
   device = forcedevice
  if forcedevice == "iphone" or forcedevice == "ipod":
   device = "apple"
  if ((mobile == False and forcemobile == False) or nomobile == True or forcedevice == "") and device != "ipad":
   device = ""
  return cgi.escape(device, True)
 else:
  return mobile
is_mobile = functools.partial(is_mobile, lambda: request.headers, lambda: request.GET)

@route("/layout/:filename#[a-zA-Z0-9\-_\.\/]+#")
def layout(filename):
 """Returns a given file located under the "layout" directory.

This is bound to the route "/layout/:filename#[a-zA-Z0-9\-_\.\/]+#".

"""
 if ".." not in filename.split("/"):
  return static_file(filename, os.path.join(config.root, "layout"))
 else:
  abort(403)

def load_yaml_file(filename, is_template=False):
 """Loads a given YAML file name into a dictionary.

If is_template is True, then the file's contents are passed through the \
template function first.

"""
 fo = open(os.path.join(config.root, filename))
 data = fo.read()
 if is_template:
  data = re.compile(r"^%(YAML|TAG)", re.MULTILINE).sub(r"%%\1", data)
  data = template(data)
 out = yaml.load(data)
 fo.close()
 return out

def not_modified(*files):
 """Raises an HTTP 304 Not Modified header if none of the given files are \
newer than the HTTP_IF_MODIFIED_SINCE header."""
 times = []
 for i in files:
  times.append(int(os.stat(os.path.join(config.root, i)).st_mtime))
 times.sort()
 last = times[-1]
 last_str = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(last))
 ims = request.environ.get("HTTP_IF_MODIFIED_SINCE")
 if ims:
  ims = parse_date(ims.split(";")[0].strip())
  if ims != None and ims >= last:
   header = {"Date": time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())}
   raise HTTPResponse(304, header=header)
 response.headers["Last-Modified"] = last_str
 return False

@route("/robots.txt")
def robots_txt():
 """Returns the contents of the static/robots.txt file if it exists.

Bound to the route "/robots.txt".

"""
 return static_file("robots.txt", os.path.join(config.root, "static"))

def root_path():
 """Returns the root URL for the application, minus the scheme and netloc."""
 return urllib.quote(script())

def root_url():
 """Returns the full root URL for the application.

Set the FORCE_HTTPS WSGI environment variable or the X-JugOfPunch-ForceHTTPS \
header to True (case-sensitive) to force this to use the "https" scheme.  The \
environment variable takes precedence over the header if both are set.

"""
 url_ = urlparse.urlsplit(request.url)
 return urlparse.urlunsplit((url_.scheme, url_.netloc, urllib.quote(script()),
                             "", ""))

_run = run
def run(app=None, *args, **kwargs):
 """Wrapper for Bottle's run function.

A JugOfPunchMiddleware is added to the app before it is run.

"""
 app = app or default_app()
 if isinstance(app, basestring):
  app = load_app(app)
 app = JugOfPunchMiddleware(app)
 _run(app=app, *args, **kwargs)

def run_if_main(name, dev=False, host=None, port=None, parse_args=True, *args,
                **kwargs):
 """Runs the application if the given name is "__main__".

Optional arguments:
 dev: specifies whether development mode is enabled; defaults to False
 host: host name to bind to; defaults to config.development.host
 port: port number to bind to; defaults to config.development.port
 parse_args: whether to parse command-line arguments; defaults to True

Other arguments are passed to Bottle's run function.

"""
 if name == "__main__":
  if parse_args:
   p = optparse.OptionParser(prog=os.path.basename(sys.argv[0]))
   p.add_option("--host", "-H", default=host, help="listen on the specified"
                " interface instead of the one set in config.yaml")
   p.add_option("--port", "-p", default=port, help="listen on the specified"
                " port")
   options, args = p.parse_args()
   host, port = options.host, options.port
  if dev == True:
   debug(config.development.debug)
  run(host=host or config.development.host,
      port=port or config.development.port, *args, **kwargs)

def sanitize(value, exclude=[], optional={}):
 # TODO:  Figure out what the hell this does
 if isinstance(value, list):
  out = []
  for i in value:
   out.append(sanitize(i, exclude))
 elif isinstance(value, dict):
  out = {}
  for i in optional:
   if i not in value:
    out[i] = optional[i]
  for i in value:
   if i in exclude:
    out[i] = value[i]
   else:
    out[i] = sanitize(value[i], exclude)
 elif value == None:
  out = ""
 elif not isinstance(value, basestring):
  out = str(value)
 else:
  out = value
 return out

def script():
 """Returns the script name.

This is usually the part of the URL's path component that is the parent of all \
URLs for this application.

The FORCE_SCRIPT_NAME WSGI environment variable or the \
X-JugOfPunch-ForceScriptName header can be used to override this value.  The \
environment variable takes precedence over the header if both are set.

"""
 # Necessary due to some stupid bug in uWSGI, Python 2.6, or something; I'm
 # not sure which
 if request.environ.get("FORCE_SCRIPT_NAME", ""):
  return request.environ["FORCE_SCRIPT_NAME"].rstrip("/")
 elif request.environ.get("HTTP_X_JUGOFPUNCH_FORCESCRIPTNAME", ""):
  return request.environ["HTTP_X_JUGOFPUNCH_FORCESCRIPTNAME"].rstrip("/")
 elif "REQUEST_URI" in request.environ:
  REQUEST_URI = urlparse.urlsplit(request.environ.get("REQUEST_URI", "")).path
  REQUEST_URI = urllib.unquote(REQUEST_URI)
  if request.path == "/":
   REQUEST_URI = REQUEST_URI.rstrip("/") + "/"
  return REQUEST_URI.rsplit(request.path, 1)[0].rstrip("/")
 else:
  return request.environ.get("SCRIPT_NAME", "").rstrip("/")

def setattrs(d, _cls=None):
 """Creates a class object that contains the given dictionary's keys as \
attributes."""
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

def strip_html(value, exclude=[]):
 """Attempts to remove HTML from a given string.

Lists and dictionaries are handled recursively.  The optional exclude argument \
specifies dictionary keys that are not to be processed.

"""
 if isinstance(value, list):
  out = []
  for i in value:
   out.append(strip_html(i))
 elif isinstance(value, dict):
  out = {}
  for i in value:
   if i in exclude:
    out[i] = value[i]
   else:
    out[i] = strip_html(value[i])
 elif isinstance(value, basestring):
  out = re.compile(r"<.*?>").sub("", value)
 else:
  out = value
 return out

@route("/static/:filename#[a-zA-Z0-9\-_\.\/]+#")
def static(filename):
 """Returns a given file located under the "static" directory.

This is bound to the route "/static/:filename#[a-zA-Z0-9\-_\.\/]+#".

"""
 if ".." not in filename.split("/"):
  return static_file(filename, os.path.join(config.root, "static"))
 else:
  abort(403)

_template = template
def template(tpl_name, template_adapter=None, _passthrough=False, **tplvars):
 """Extension of Bottle's template function."""
 if not template_adapter:
  template_adapter = config.template.engine
 kwargs = tplvars
 if not _passthrough:
  kwargs = generate_tplvars(template_adapter, **tplvars)
 return _template(tpl_name, template_adapter=template_adapter, **kwargs)

# from Bottle
mako_template = functools.partial(template, template_adapter=MakoTemplate)
cheetah_template = functools.partial(template, template_adapter=CheetahTemplate)
jinja2_template = functools.partial(template, template_adapter=Jinja2Template)

def to_unicode(s, encoding="utf8"):
 """Returns a Unicode version of the given object."""
 if isinstance(s, unicode):
  return s
 if isinstance(s, (str, buffer)):
  return unicode(s, encoding)
 return unicode(s)

def url_scheme():
 """Returns the URL scheme for the current request.

Set the FORCE_HTTPS WSGI environment variable or the X-JugOfPunch-ForceHTTPS \
header to True (case-sensitive) to force this to return "https".  The \
environment variable takes precedence over the header if both are set. \

"""
 return urlparse.urlsplit(request.url).scheme

# from Bottle
def view(tpl_name, template_adapter=None, **tplvars):
 """Extension of Bottle's view function."""
 if not template_adapter:
  template_adapter = config.template.engine
 def decorator(func):
  @functools.wraps(func)
  def wrapper(*args, **kwargs):
   result = func(*args, **kwargs)
   if isinstance(result, dict):
    tplvars_ = tplvars.copy()
    tplvars_.update(result)
    return template(tpl_name, template_adapter, **tplvars_)
   return result
  return wrapper
 return decorator

# from Bottle
mako_view = functools.partial(view, template_adapter=MakoTemplate)
cheetah_view = functools.partial(view, template_adapter=CheetahTemplate)
jinja2_view = functools.partial(view, template_adapter=Jinja2Template)
