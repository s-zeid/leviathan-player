/* DerpScrubber
 * A simple JavaScript scrubber/slider widget.
 *
 * Copyright (C) 2011 Scott Zeid
 * https://github.com/scottywz/DerpScrubber
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 *
 * Except as contained in this notice, the name(s) of the above copyright holders
 * shall not be used in advertising or otherwise to promote the sale, use or
 * other dealings in this Software without prior written authorization.
 *
 */

var DerpScrubber = (function() {
 var $ = jQuery;
 
 function DerpScrubber(width, height, barSize, barBG, highlightBG, availableBG,
                       outerBG, handle, clickable) {
  if (typeof(width) == "object") {
   var obj = width;
   this.width = width = obj.width;
   this.height = height = obj.height;
   this.barSize = barSize = obj.barSize;
   this.barBG = barBG = obj.barBG;
   this.highlightBG = highlightBG = obj.highlightBG;
   this.availableBG = availableBG = obj.availableBG;
   this.outerBG = outerBG = obj.outerBG;
   this.handle = handle = obj.handle;
   this.clickable = clickable = obj.clickable;
   delete obj;
  } else {
   this.width = width;
   this.height = height;
   this.barSize = barSize;
   this.barBG = barBG;
   this.highlightBG = highlightBG;
   this.availableBG = availableBG;
   this.outerBG = outerBG;
   this.handle = handle;
   this.clickable = clickable;
  }
  
  if (typeof(this.clickable) == "undefined")
   this.clickable = clickable = true;
  
  this.handleContainer = $("<span></span>");
  this.handleContainer.addClass("DerpScrubber_handleContainer");
  this.handleContainer.css("position", "absolute");
  this.handleContainer.css("top", "0").css("right", "0");
  this.handleContainer.css("bottom", "0").css("left", "0");
  this.handleContainer.css("width", "auto").css("height", "auto");
  this.handleContainer.css("display", "block").css("margin", "0");
  
  this.userHandle = typeof(handle) == "object";
  if (!this.userHandle) {
   if (handle && typeof(handle) == "string") {
    this.handle = $("<span></span>").addClass("DerpScrubber_handle");
    this.handle.css("background", handle);
    handle = this.handle;
   } else
    this.handle = handle = null;
  }
  if (this.handle) {
   this.handle.addClass("DerpScrubber_handle");
   this.handle.css("display", "inline-block").css("position", "relative");
   this.handle.css("top", "auto").css("right", "auto");
   this.handle.css("bottom", "auto").css("left", "auto");
   this.handle.css("margin", "0").css("overflow", "hidden");
   this.handleContainer.append(this.handle);
  }
  
  this.highlight = $("<span></span>").addClass("DerpScrubber_highlight");
  this.highlight.css("display", "block").css("position", "absolute");
  this.highlight.css("top", "0").css("right", "0");
  this.highlight.css("bottom", "0").css("left", "0");
  this.highlight.css("width", "100%").css("height", "100%");
  this.highlight.css("margin", "0")
  if (highlightBG) this.highlight.css("background", highlightBG);
  
  this.availableArea =$("<span></span>").addClass("DerpScrubber_availableArea");
  this.availableArea.css("display", "block").css("position", "absolute");
  this.availableArea.css("top", "0").css("right", "0");
  this.availableArea.css("bottom", "0").css("left", "0");
  this.availableArea.css("width", "100%").css("height", "100%");
  this.availableArea.css("margin", "0")
  if (availableBG) this.availableArea.css("background", availableBG);
  
  this.bar = $("<span></span>").addClass("DerpScrubber_bar");
  this.bar.css("display", "block").css("position", "absolute");
  this.bar.css("top", "0").css("right", "0");
  this.bar.css("bottom", "0").css("left", "0");
  this.bar.css("width", "auto").css("height", "auto").css("margin", "0");
  if (barBG) this.bar.css("background", barBG);
  
  this.outer = $("<span></span>").addClass("DerpScrubber_outer");
  this.outer.css("display", "block").css("position", "absolute");
  this.outer.css("top", "0").css("right", "0");
  this.outer.css("bottom", "0").css("left", "0");
  this.outer.css("width", "auto").css("height", "auto");
  this.outer.css("margin", "0").css("overflow", "hidden");
  
  this.container = $("<span></span>").addClass("DerpScrubber_container");
  this.container.css("display", "block").css("position", "relative");
  this.container.css("top", "0").css("right", "0");
  this.container.css("bottom", "0").css("left", "0");
  this.container.css("width", "100%").css("height", "100%");
  this.container.css("margin", "0").css("overflow", "hidden");
  
  this.root = $("<span></span>").addClass("DerpScrubber");
  this.root.css("display", "inline-block").css("text-align", "left");
  this.root.css("width", width).css("height", height);
  if (outerBG) this.root.css("background", outerBG);
  
  if (this.root.width() > this.root.height())
   this.orientation = "horizontal";
  else
   this.orientation = "vertical";
  
  this.root.addClass("DerpScrubber_" + this.orientation);
  this.root.addClass("DerpScrubber_" + ((handle) ? "hasHandle" : "noHandle"));
  
  this.bar.append(this.availableArea);
  this.bar.append(this.highlight);
  this.outer.append(this.bar);
  this.container.append(this.outer);
  this.container.append(this.handleContainer);
  this.root.append(this.container);
  
  this.allBorders = {x: 0, y: 0};
  this.callbacks = {move: new Array(),
                    moveFinished: new Array(),
                    userMove: new Array(),
                    userMoveFinished: new Array()
                    };
  this.userMoveLock = false;
  
  this.setClickable(clickable).setEnabled(false);
  this.root.bind("mousedown.DerpScrubber", this.makeDragHandler());
  
  return this;
 }
 
 DerpScrubber.prototype = {
  adjustBox: function() {
   var outer = this.outer, bar = this.bar, root = this.root, center;
   var handle = this.handle, container = this.container, handleMargin;
   var handleOffset;
   if (this.orientation == "horizontal") {
    this.highlight.css("width", "0%");
    this.highlight.css("right", "auto");
    this.availableArea.css("right", "auto");
    if (typeof(this.barSize) == "string")
     bar.css("height", this.barSize);
   } else {
    this.highlight.css("height", "0%");
    this.highlight.css("top", "auto");
    this.availableArea.css("top", "auto");
    if (typeof(this.barSize) == "string")
     bar.css("width", this.barSize);
   }
   center = this.getHandleSize() / 2;
   var barBorderX = Math.abs(bar.outerWidth() - bar.width()) / 2;
   var barBorderY = Math.abs(bar.outerHeight() - bar.height()) / 2;
   var outerBorderX = Math.abs(root.width() - outer.outerWidth()) / 2;
   var outerBorderY = Math.abs(root.height() - outer.outerHeight()) / 2;
   var rootBorderX = (root.outerWidth() - root.width()) / 2;
   var rootBorderY = (root.outerHeight() - root.height()) / 2;
   var rootPaddingX = (outer.outerWidth() - root.width()) / 2;
   var rootPaddingY = (outer.outerHeight() - root.height()) / 2;
   this.allBorders.x = (barBorderX + outerBorderX + rootBorderX) * 2;
   this.allBorders.y = (barBorderY + outerBorderY + rootBorderY) * 2;
   if (this.orientation == "horizontal") {
    outer.css("height", String(outer.height() - outerBorderY * 2) + "px");
    if (bar.height() >= outer.height())
     bar.css("height", String(bar.height() - barBorderY * 2) + "px");
    var barMarginY = (outer.height() - bar.outerHeight()) / 2;
    bar.css("top", Math.max(barMarginY, 0) + "px");
    bar.css("bottom", Math.max(barMarginY, 0) + "px");
    bar.css("left", String(center - barBorderX) + "px");
    bar.css("right", String(center - barBorderX) + "px");
   } else {
    outer.css("width", String(outer.width() - outerBorderX * 2) + "px");
    if (bar.width() >= outer.width())
     bar.css("width", String(bar.width() - barBorderX * 2) + "px");
    var barMarginX = (outer.width() - bar.outerWidth()) / 2;
    bar.css("top", String(center - barBorderX) + "px");
    bar.css("bottom", String(center - barBorderX) + "px");
    bar.css("left", Math.max(barMarginX, 0) + "px");
    bar.css("right", Math.max(barMarginX, 0) + "px");
   }
   if (handle) {
    this.handleContainer.css("display", "block");
    if (this.orientation == "horizontal") {
     if (!this.userHandle) {
      handle.css("width", this.handleContainer.height() / 2);
      if (!handle.height()) this.handle.css("height", this.height);
      handleBorderX = Math.abs(handle.outerWidth() - handle.width());
      handleBorderY = Math.abs(handle.outerHeight() - handle.height());
      handle.css("width", handle.width() - handleBorderX);
      handle.css("height", handle.height() - handleBorderY);
     }
     center = this.getHandleSize() / 2;
     handleMargin = (this.container.height() - this.handle.outerHeight()) / 2;
     handle.css("margin-top", String(Math.floor(handleMargin) + "px"));
     handle.css("margin-left", String(-center) + "px");
     bar.css("left", String(center) + "px");
     bar.css("right", String(center) + "px");
     handleOffset = this.getBarOffset()-this.getOffsetOf(this.handleContainer);
     this.handleContainer.css("left", String(handleOffset) + "px");
     this.handleContainer.css("right", String(handleOffset) + "px");
    } else {
     if (!this.userHandle) {
      if (!handle.width()) this.handle.css("width", this.width);
      handle.css("height", this.handleContainer.width() / 2);
      handleBorderX = Math.abs(handle.outerWidth() - handle.width());
      handleBorderY = Math.abs(handle.outerHeight() - handle.height());
      handle.css("width", handle.width() - handleBorderX);
      handle.css("height", handle.height() - handleBorderY);
     }
     center = this.getHandleSize() / 2;
     handleMargin = (this.container.width() - this.handle.outerwidth()) / 2;
     handle.css("margin-left", String(Math.floor(handleMargin) + "px"));
     handle.css("margin-top", String(-center) + "px");
     bar.css("top", String(center) + "px");
     bar.css("bottom", String(center) + "px");
     handleOffset = this.getBarOffset()-this.getOffsetOf(this.handleContainer);
     handleContainer.css("top", String(handleOffset) + "px");
     handleContainer.css("bottom", String(handleOffset) + "px");
    }
   }
   if (this.enabled)
    this.handleContainer.css("display", (this.clickable) ? "block" : "none");
   else
    this.handleContainer.css("display", "none");
   return this;
  },
  
  appendTo: function(element) {
   $(element).append(this.root);
   return this.adjustBox();
  },
  
  bind: function(eventType, callback) {
   if (typeof(eventType) == "object") {
    for (type in eventType)
     this.bind(type, eventType[type]);
    return this;
   }
   this.callbacks[eventType].push(callback);
   return this;
  },
  
  disable: function() {
   this.setEnabled(false);
   return this;
  },
 
  enable: function() {
   this.setEnabled(true);
   return this;
  },
  
  getAvailableSize: function() {
   return this.getSizeOf(this.availableArea);
  },
  
  getAvailableCoefficient: function() {
   var barSize = this.getSizeOf(this.bar);
   return (barSize > 0) ? this.getSizeOf(this.availableArea) / barSize : 1;
  },
  
  getAvailablePercent: function() {
   return this.getAvailableCoefficient() * 100;
  },
  
  getCoefficient: function(position) {
   if (typeof(position) != "number" && !this.enabled) return null;
   if (typeof(position) != "number") position = this.getPosition();
   return position / this.getBarSize();
  },
  
  getBarOffset: function() {
   return this.getOffsetOf(this.bar);
  },
  
  getBarSize: function() {
   return this.getSizeOf(this.bar);
  },
  
  getHandleSize: function() {
   return (this.handle) ? this.getOuterSizeOf(this.handle) : 0;
  },
  
  getHighlightOffset: function() {
   return this.getOffsetOf(this.highlight);
  },
  
  getHighlightSize: function() {
   return this.getSizeOf(this.highlight);
  },
  
  getOffsetOf: function(element) {
   var offset;
   // All this shit is necessary to account for borders
   if (this.orientation == "horizontal") {
    offset = element.offset().left;
    offset += (element.outerWidth(true) - element.width()) / 2;
   } else {
    offset = element.offset().top;
    offset += (element.outerHeight(true) - element.height()) / 2;
   }
   return offset;
  },
  
  getOuterSizeOf: function(element) {
   if (this.orientation == "horizontal")
    return element.outerWidth();
   return element.outerHeight();
  },
  
  getSizeOf: function(element) {
   if (this.orientation == "horizontal")
    return element.width();
   return element.height();
  },
  
  getPercent: function(position) {
   if (typeof(position) != "number" && !this.enabled) return null;
   return this.getCoefficient(position) * 100;
  },
  
  getPosition: function() {
   if (typeof(position) != "number" && !this.enabled) return null;
   return this.getHighlightSize();
  },
  
  makeDragHandler: function() {
   var scrubber = this;
   function doMove(event, last) {
    // Prevents text from being selected
    event.preventDefault();
    scrubber.moveUser(event, last);
   }
   function doUnbind(event) {
    event.preventDefault();
    scrubber.moveUser(event, true);
    $(window).unbind("mousemove", doMove).unbind("mouseup", doUnbind);
   }
   function handler(event) {
    event.preventDefault();
    // Left mouse button only
    if (event.which == 1 && scrubber.clickable && scrubber.enabled) {
     doMove(event);
     $(window).mousemove(doMove).mouseup(doUnbind);
    }
   }
   return handler;
  },
  
  move: function(position, user, last) {
   var position, coeff, percent, info, extra;
   var barSize = this.getBarSize();
   user = Boolean(user);
   last = Boolean((user) ? last : true);
   if (!user && this.userMoveLock)
    return this;
   if (typeof(position) != "number") {
    if (typeof(position) == "string" && position.match(/^[0-9.]+\%$/g))
     position = (Number(position.replace("%","")) / 100) * barSize;
    else if (typeof(position) == "string" && position != "" &&
             Number(position) != NaN)
     position = Number(position);
    if (typeof(position) != "number")
     position = 0;
   }
   position = Math.min(barSize, Math.max(position, 0));
   coeff = position / ((barSize) ? barSize : position);
   percent = coeff * 100;
   if (this.orientation == "horizontal")
    this.highlight.css("width", String(percent) + "%");
   else
    this.highlight.css("height", String(percent) + "%");
   this.moveHandle(percent);
   info = {scrubber: this, position: position, coefficient: coeff,
           percent: percent, user: user, last: last};
   this.onMove(null, info);
   if (last)
    this.onMoveFinished(null, info);
   if (user) {
    this.onUserMove(null, info);
    if (last) {
     this.onUserMoveFinished(null, info);
     this.userMoveLock = false;
    }
   }
   return this;
  },
  
  moveHandle: function(percent) {
   if (!this.handle)
    return this;
   if (typeof(percent) != "number")
    percent = this.getPercent();
   if (this.orientation == "horizontal")
    this.handle.css("left", String(percent) + "%");
   else
    this.handle.css("top", String(percent) + "%");
   return this;
  },
  
  moveUser: function(event, last) {
   this.userMoveLock = true;
   if (this.orientation == "horizontal")
    position = event.pageX - this.getBarOffset();
   else
    position = this.getOffsetOf(this.outer) + this.getBarSize() - event.pageY;
   return this.move(position, true, last);
  },
  
  moveToCoefficient: function(coeff) {
   return this.moveToPercent(Number(coeff) * 100);
  },
  
  moveToPercent: function(percent) {
   if (typeof(percent) == "number")
    percent = String(Math.max(0, Math.min(percent, 100))) + "%";
   if (typeof(percent) != "string" || !percent.match(/^[0-9.]+\%?$/g))
    if (percent == null || percent == "" || Number(percent) == NaN)
     percent = "100%";
   if (!percent.match(/^[0-9.]+\%$/g)) percent = percent + "%";
   return this.move(percent);
  },
  
  _onEvent: function(eventType, callback, _info) {
   if (typeof(callback) != "function")
    this.trigger(eventType, callback, _info);
   else
    this.bind(eventType, callback);
   return this;
  },
  
  onMove: function(callback, _info) {
   return this._onEvent("move", callback, _info);
  },
  
  onMoveFinished: function(callback, _info) {
   return this._onEvent("moveFinished", callback, _info);
  },
  
  onUserMove: function(callback, _info) {
   return this._onEvent("userMove", callback, _info);
  },
  
  onUserMoveFinished: function(callback, _info) {
   return this._onEvent("userMoveFinished", callback, _info);
  },
  
  prependTo: function(element) {
   $(element).prepend(this.root);
   return this.adjustBox();
  },
  
  removeFrom: function(element) {
   $(element).remove(this.root);
   return this;
  },
  
  reset: function() {
   this.disable();
   this.move(0);
   this.setAvailableSize("100%");
   return this;
  },
  
  setAvailableCoefficient: function(coeff) {
   coeff = Math.max(0, Math.min(coeff, 1));
   return this.setAvailableSize(String(Number(coeff) * 100) + "%");
  },
  
  setAvailablePercent: function(percent) {
   if (typeof(percent) == "number")
    percent = String(Math.max(0, Math.min(percent, 100))) + "%";
   if (typeof(percent) != "string" || !percent.match(/^[0-9.]+\%?$/g))
    if (percent == null || percent == "" || Number(percent) == NaN)
     percent = "100%";
   if (!percent.match(/^[0-9.]+\%$/g)) percent = percent + "%";
   return this.setAvailableSize(percent);
  },
  
  setAvailableSize: function(size) {
   if (typeof(size) == "number")
    size = String(Math.min(0, Math.max(size / this.getBarSize(), 1))) + "%";
   else if (typeof(size) != "string" || !size.match(/^[0-9.]+\%$/g))
    if (percent == null || percent == "" || String(Number(size)) == NaN)
     size = "100%";
   if (this.orientation == "horizontal")
    this.availableArea.css("width", size);
   else
    this.availableArea.css("height", size);
   return this;
  },
  
  setClickable: function(clickable) {
   this.clickable = Boolean(clickable);
   if (clickable) {
    this.handleContainer.css("display", (this.enabled) ? "block" : "none");
    this.root.removeClass("DerpScrubber_notClickable");
    this.root.addClass("DerpScrubber_clickable");
   } else {
    this.handleContainer.css("display", "none");
    this.root.removeClass("DerpScrubber_clickable");
    this.root.addClass("DerpScrubber_notClickable");
   }
   return this;
  },
  
  setEnabled: function(enabled) {
   this.enabled = Boolean(enabled);
   if (enabled) {
    this.handleContainer.css("display", (this.clickable) ? "block" : "none");
    this.availableArea.css("display", "block");
    this.highlight.css("display", "block");
    this.onMove();
    this.onMoveFinished();
    this.root.removeClass("DerpScrubber_disabled");
    this.root.addClass("DerpScrubber_enabled");
   } else {
    this.highlight.css("display", "none");
    this.availableArea.css("display", "none");
    this.handleContainer.css("display", "none");
    this.root.removeClass("DerpScrubber_enabled");
    this.root.addClass("DerpScrubber_disabled");
   }
   return this;
  },
  
  trigger: function(eventType, extra, info) {
   if ($.isArray(eventType)) {
    for (var i = 0; i < eventType.length; i++)
     this.trigger(eventType[i]);
    return this;
   }
   if (typeof(info) == "undefined")
    info = {scrubber: this, position: this.getPosition(),
            coefficient: this.getCoefficient(), percent: this.getPercent()};
   if (typeof(extra) == "object") {
    for (key in extra)
     info[key] = extra[key];
   }
   for (var i = 0; i < this.callbacks[eventType].length; i++) {
    this.callbacks[eventType][i](info);
   }
  },
  
  unbind: function(eventType, callback) {
   if ($.isArray(eventType)) {
    for (var i = 0; i < eventType.length; i++)
     this.trigger(eventType[i]);
    return this;
   }
   if (typeof(eventType) == "object") {
    for (type in eventType)
     this.unbind(type, eventType[type]);
    return this;
   }
   if (typeof(callback) == "undefined")
    this.callbacs[eventType].splice(0);
   else {
    for (var i = 0; i < this.callbacks[eventType].length; i++) {
     if (this.callbacks[eventType][i] == callback)
      this.callbacks[eventType].splice(i, 1);
    }
   }
   return this;
  }
 };
 
 return DerpScrubber;
})();
