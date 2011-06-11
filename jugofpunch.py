# -*- coding: utf-8 -*-

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
 class development: pass
 class template:
  defaults = dict()
  engine = SimpleTemplate
  title_format = "%(page)s - %(site)s"
 
 _default_config_file = "config.yaml"
 
 @classmethod
 def __init__(self, config_file = True, root = None):
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
 def load(self, fname = _default_config_file):
  self._dict = load_yaml_file(abspath(fname))
  setattrs(self._dict, self)
  if self.root != self._root:
   self._root = self.root
   os.chdir(self.root)
  debug(False)

def abspath(path):
 return os.path.join(config.root, path)

def args():
 path = request.path.split("/")
 path[0] = script()
 return path

@route("/favicon.ico")
@route("/favicon.png")
def favicon():
 if request.path == "/favicon.ico":
  return static_file("favicon.ico", os.path.join(config.root, "static"))
 elif request.path == "/favicon.png":
  return static_file("favicon.png", os.path.join(config.root, "static"))

def generate_tplvars(template_adapter = None, **kwargs):
 if not template_adapter:
  template_adapter = config.template.engine
 tplvars = getattr(config.template, "defaults", {}).copy()
 tplvars.update(kwargs)
 site_name = tplvars.get("site_name", config.name)
 if "handler" not in tplvars:
  tplvars["handler"] = handler()
 if "page_title" not in tplvars:
  if "page_name" in tplvars:
   tplvars["page_title"] = config.template.title_format % dict(page=tplvars["page_name"], site=site_name)
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
 tplvars["ua"] = request.header.get("User-Agent", "")
 tplvars["wii"] = "wii" in request.header.get("User-Agent", "").lower() or "forcewii" in request.GET
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
 try:
  return app().match_url(request.path)[0].func_name
 except HTTPError:
  return "error"

def htmlentities(text, exclude = "\"&<>", table = htmlentitydefs.codepoint2name):
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

htmlspecialchars = functools.partial(htmlentities, exclude="", table={34: "quot", 38: "amp", 60: "lt", 62: "gt"})

@route("/images/:filename#[a-zA-Z0-9\-_\.\/]+#")
def images(filename):
 if ".." not in filename.split("/"):
  return static_file(filename, os.path.join(config.root, "images"))
 else:
  abort(403)

def is_mobile(headers, GET, return_device = False):
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
is_mobile = functools.partial(is_mobile, lambda: request.header, lambda: request.GET)

@route("/layout/:filename#[a-zA-Z0-9\-_\.\/]+#")
def layout(filename):
 if ".." not in filename.split("/"):
  return static_file(filename, os.path.join(config.root, "layout"))
 else:
  abort(403)

def load_yaml_file(filename, is_template = False):
 fo = open(os.path.join(config.root, filename))
 data = fo.read()
 if is_template:
  data = re.compile(r"^%(YAML|TAG)", re.MULTILINE).sub(r"%%\1", data)
  data = template(data)
 out = yaml.load(data)
 fo.close()
 return out

def not_modified(*files):
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
 return static_file("robots.txt", os.path.join(config.root, "static"))

def root_path():
 return urllib.quote(script())

def root_url():
 url_ = urlparse.urlsplit(request.url)
 return urlparse.urlunsplit((url_.scheme, url_.netloc, urllib.quote(script()), "", ""))

def run_if_main(name, dev=False, host=None, port=None, parse_args=True, *args,
                **kwargs):
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
 if "FORCE_SCRIPT_NAME" in request.environ:
  return request.environ.get("FORCE_SCRIPT_NAME", "").rstrip("/")
 if "REQUEST_URI" in request.environ:
  REQUEST_URI = urlparse.urlsplit(request.environ.get("REQUEST_URI", "")).path
  REQUEST_URI = urllib.unquote(REQUEST_URI)
  if request.path == "/":
   REQUEST_URI = REQUEST_URI.rstrip("/") + "/"
  return REQUEST_URI.rsplit(request.path, 1)[0].rstrip("/")
 else:
  return request.environ.get("SCRIPT_NAME", "").rstrip("/")

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

def strip_html(value, exclude = []):
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
 if ".." not in filename.split("/"):
  return static_file(filename, os.path.join(config.root, "static"))
 else:
  abort(403)

_template = template
def template(tpl_name, template_adapter = None, _passthrough = False, **tplvars):
 if not template_adapter:
  template_adapter = config.template.engine
 kwargs = tplvars
 if not _passthrough:
  kwargs = generate_tplvars(template_adapter, **tplvars)
 return _template(tpl_name, template_adapter, **kwargs)

# from Bottle
mako_template = functools.partial(template, template_adapter=MakoTemplate)
cheetah_template = functools.partial(template, template_adapter=CheetahTemplate)
jinja2_template = functools.partial(template, template_adapter=Jinja2Template)

def to_unicode(s, encoding="utf8"):
 if isinstance(s, unicode):
  return s
 if isinstance(s, (str, buffer)):
  return unicode(s, encoding)
 return unicode(s)

def url_scheme():
 return urlparse.urlsplit(request.url).scheme

# from Bottle
def view(tpl_name, template_adapter = None, **tplvars):
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
