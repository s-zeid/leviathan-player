/*
 * Leviathan Music Player
 * A Web-based music player based on the Leviathan music library manager.
 * 
 * Copyright (C) 2010-2011 Scott Zeid
 * http://me.srwz.us/leviathan/web
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

var PREVIOUS_NO_REPLAY_THRESHOLD = 3;

var buffered_percent = 0;
var $player = null;
var play_history = [];
var player = null;
var previous_button_last_pressed = 0;
var repeat = true;
var scrobble_threshold = null;
var scrobbled = false;
var scrobbling = false;
var scrubber_seek = null;
var scrubber_volume = null;
var seek_interval = null;
var shuffle = false;
var song_length = 0;

function add_link_clicked(event) {
 add_to_queue($(this).parent(".row").parent(".table").parent("li"));
 if ($("#play_pause .no_play").css("display") == "none")
  update_prev_next_buttons();
}

function add_to_queue(el) {
 var category = el.attr("data-category");
 if (category == "album" || category == "playlist" || category == "songs") {
  queue_push_one(el);
 } else if (el.children(".children").children("ul").length == 1 &&
            category != "artists") {
  queue_push_each(el.children(".children").children("ul").first());
 } else {
  var url = get_list_url(el, "add", "json");
  var tmp = $("<div></div>");
  insert_list_from_json_url(url, tmp, function() {
   queue_push_each(tmp.children("ul"));
   tmp.html("");
  });
 }
}

function cat_type_map(category, action) {
 if (category == "queue" ||category == "album" || category == "playlist" ||
     category == "songs")
  return "song";
 if (category == "albums" || category == "artist")
  return "album";
 if (category == "artists" && action == "expand")
  return "albums"
 if (category == "artists")
  return "artist";
 if (category == "playlists")
  return "playlist";
 return "";
}

function clear_queue(update_dom) {
 get_queue_el().html("");
 play_history = [];
 update_prev_next_buttons();
 stop_playing();
}

function get_current_song_element() {
 return $("#" + $("#song_info").attr("data-song-dom-id"));
}

function get_list_el_from_json(json) {
 var ul = $("<ul></ul>");
 var category = json.category;
 var entries = json.entries;
 ul.addClass(category);
 for (var i = 0; i < entries.length; i++) {
  var li = $("<li></li>");
  li.attr("id", entries[i].dom_id).attr("data-category", category);
  li.attr("data-id", entries[i].data_id).attr("data-name", entries[i].name);
  li.attr("data-full-name", entries[i].full_name);
  li.attr("data-artist", entries[i].data_artist);
  li.attr("data-icon", entries[i].icon);
  if (entries[i].song !== null) {
   li.attr("data-song-url", entries[i].song.url);
   li.attr("data-song-art-directory", entries[i].song.art_directory);
   li.attr("data-song-title", entries[i].song.title);
   li.attr("data-song-artist", entries[i].song.artist);
   li.attr("data-song-album", entries[i].song.album);
   if (entries[i].song.length != null)
    li.attr("data-song-length", entries[i].song.length);
   else
    li.attr("data-song-length", "-1")
  }
  var table = $("<div></div>").addClass("table");
  var row = $("<div></div>").addClass("row");
  row.append($("<span></span>").addClass("spacer"));
  if (entries[i].icon != "") {
   var icon_url = entries[i].icon.replace("'", "\\'");
   var icon = $("<span></span>").addClass("icon");
   icon.css("background-image", "url('" + icon_url + "')")
   row.append(icon);
  }
  row.append($("<span></span>").addClass("name").text(entries[i].name));
  row.children("span").click(row_clicked);
  var add = $("<span></span>").addClass("add").click(add_link_clicked);
  row.append(add);
  var remove = $("<span></span>").addClass("remove").click(remove_link_clicked);
  row.append(remove);
  if (category == "queue")
   add.hide();
  else
   remove.hide();
  table.append(row);
  li.append(table);
  var children = $("<div></div>").addClass("children");
  li.append(children);
  ul.append(li);
 }
 var border = $("<li></li>").addClass("border");
 ul.append(border);
 return ul;
}

function get_list_url(el, action, type) {
 var dom_id = el.attr("id");
 var category = el.attr("data-category");
 var id = el.attr("data-id");
 var artist = el.attr("data-artist");
 var url = "{{root_url}}/list/";
 var file = "";
 if (type == "json")
  file = "list.json";
 else if (type == "xspf")
  file = "xspf.xml";
 if (category == "album" || category == "playlist" || category == "songs") {
  return ""
 } else if (category == "top") {
  url += id + "/" + file + "?";
 } else {
  url += cat_type_map(category, action) + "/" + file;
  if (category == "albums")
   url += "?artist=" + artist + "&id=" + id;
  else
   url += "?id=" + id;
  url += "&";
 }
 url += "parent=" + dom_id;
 return url
}

function get_queue_el() {
 return $("#queue").children("div").children(".list").children("ul.queue");
}

function get_scrobble_threshold(duration) {
 var threshold = null;
 if (duration > 30) {
  if (duration > 480)
   threshold = 240;
  else
   threshold = Math.round(duration / 2);
 }
 return threshold;
}

function hide_large_artwork() {
 $("#large_art_lightbox").fadeOut(400, function() {
  $("#large_art_lightbox").remove();
 });
}

function init_player() {
 var play_event_callback = function() {
  // The play event is sent in jPlayer Flash mode when the player is un-paused
  // AND when playback of a song initially starts.  This differs from the HTML5
  // spec, which says that this should be sent only when un-paused.  The
  // playing event is NOT emulated in Flash mode, so I moved the code here and
  // assigned it to both events.  This has the consequence of the code being
  // run twice in HTML5 mode, but the resource use in that case should be
  // trivial.
  
  $("#play_pause .no_play").hide();
  $("#play_pause .play").hide();
  $("#play_pause .pause").show();
  set_icon_url(get_current_song_element(), "{{root_url}}/images/play.png");
 }
 $player = $("#player").jPlayer({
  emulateHtml: true,
  muted: false,
  preload: "auto",
  size: {width: 1, height: 0},
  solution: "html,flash",
  supplied: "mp3",
  swfPath: "{{root_path}}/static",
  loop: false,
  volume: 1,
  wmode: "window",
  ready: function() {
   $(this).jPlayer("unmute");
   //$(this).jPlayer("volume", 1);
   update_volume_bar(this.volume);
   scrubber_volume.enable();
  },
  progress: function(e) {
   var buffered = buffered_percent = e.jPlayer.status.seekPercent;
   var duration = e.jPlayer.status.duration;
   if (buffered && duration) scrubber_seek.setAvailablePercent(buffered);
   if (buffered == 100 && !scrobbled && scrobble_threshold == null) {
    scrobble_threshold = get_scrobble_threshold(duration);
    update_now_playing(get_current_song_element(), duration);
   }
  },
  ended: function() { play_next_song(); },
  volumechange: function() {
   update_volume_icon(player.muted);
   scrubber_volume.setEnabled(!player.muted);
   if (!player.muted)
    update_volume_bar(player.volume);
  },
  pause: function() {
   // Don't change icon when switching tracks
   setTimeout(function() {
    if (player.src) {
     $("#play_pause .no_play").hide();
     $("#play_pause .pause").hide();
     $("#play_pause .play").show();
     set_icon_url(get_current_song_element(), "{{root_url}}/images/pause.png");
    }
   }, 10);
  },
  play: play_event_callback,
  playing: play_event_callback
 });
 player = $player[0];
}

function init_ui() {
 scrubber_seek = new DerpScrubber({
  width: "100%", height: "24px", barSize: "6px", outerBG: "transparent",
  highlightBG: "{{!theme['scrubber'][0]}}",
  availableBG: "{{!theme['scrubber'][1]}}",
  barBG: "{{!theme['scrubber'][2]}}",
  handle: $("<span></span>").addClass("scrubber-handle")
 }).onUserMove(scrubber_seek_changed).onUserMoveFinished(function() {
  setTimeout("seek_interval = setInterval(seek_interval_callback, 250);", 250);
 }).appendTo("#seek_scrubber");
 scrubber_volume = new DerpScrubber({
  width: "100%", height: "24px", barSize: "6px", outerBG: "transparent",
  highlightBG: "{{!theme['scrubber'][0]}}",
  availableBG: "{{!theme['scrubber'][1]}}",
  barBG: "{{!theme['scrubber'][2]}}",
  handle: $("<span></span>").addClass("scrubber-handle")
 }).onUserMove(scrubber_volume_changed).appendTo("#volume_scrubber");
 $("#artwork .generic").click(function() { show_large_artwork(); });
 $("#previous .previous").click(function() { play_previous_song(); });
 $("#play_pause .play").click(function() { player_play(); });
 $("#play_pause .pause").click(function() { player_pause(); });
 $("#next .next").click(function() { play_next_song(); });
 $("#volume_button img").click(function() { toggle_mute(); });
 $("#repeat .repeat").click(function() { set_repeat(false); });
 $("#repeat .no_repeat").click(function() { set_repeat(true); });
 $("#scrobbling .scrobbling").click(function() { set_scrobbling(false); });
 $("#scrobbling .no_scrobbling").click(function() { set_scrobbling(true); });
 $("#shuffle .shuffle").click(function() { set_shuffle(false); });
 $("#shuffle .no_shuffle").click(function() { set_shuffle(true); });
 $("#categories > div > div.list").scrollTop(0);
 $("#queue > div > .header .clear").click(function() { clear_queue() });
 $("#queue > div > div.list").scrollTop(0);
 $("#artists, #albums, #playlists, #songs").each(function() {
  $(this).children(".table").children(".row").children("span").click(
   row_clicked
  );
 });
 $("#songs .table .row .add").unbind("click").click(add_link_clicked);
 reset_seek_bar();
 set_repeat({{"true" if settings["defaults"]["repeat"] else "false"}});
 set_scrobbling({{"true" if settings["defaults"]["scrobbling"] else "false"}});
 set_shuffle({{"true" if settings["defaults"]["shuffle"] else "false"}});
 $(document).keypress(key_pressed);
 init_player();
 setInterval(function() {
  if (buffered_percent && !player.paused && scrobbled == false &&
      scrobble_threshold != null && player.currentTime >= scrobble_threshold &&
      Number($("#song_info").attr("data-start-time")) + scrobble_threshold
       <= Math.round($.now() / 1000)) {
   scrobbled = true;
   scrobble(get_current_song_element(), $("#song_info").attr("data-start-time"),
            player.duration);
  }
 }, 1000);
 seek_interval = setInterval(seek_interval_callback, 250);
}

function insert_list_from_json_url(url, el, callback) {
 $.getJSON(url, function(data) {
  el.html("");
  el.append(get_list_el_from_json(data));
  if (typeof(callback) == "function")
   callback();
 });
}

function key_pressed(e) {
 var action;
 var mod = (e.ctrlKey || e.shiftKey || e.altKey);
 // Play/Pause - Space, Ctrl + P, or Ctrl + Down
 if ((e.which == 32 && !mod) || ((e.which == 112 || e.keyCode == 40) && mod))
  action = function() { player_toggle(); };
 // Previous Song - P or Ctrl + Left
 else if (((e.which == 112 && !mod) || (e.keyCode == 37 && mod)) &&
          $("#previous .previous").css("display") != "none")
  action = function() { play_previous_song(); };
 // Next Song - N or Ctrl + Right
 else if (((e.which == 110 && !mod) || (e.keyCode == 39 && mod)) &&
          $("#next .next").css("display") != "none")
  action = function() { play_next_song(); };
 // Repeat - R
 else if (e.which == 114 && !mod) {
  if ($("#repeat .repeat").css("display") != "none")
   action = function() { set_repeat(false); };
  else if ($("#repeat .no_repeat").css("display") != "none")
   action = function() { set_repeat(true); };
 }
 // Shuffle - S
 else if (e.which == 115 && !mod) {
  if ($("#shuffle .shuffle").css("display") != "none")
   action = function() { set_shuffle(false); };
  else if ($("#shuffle .no_shuffle").css("display") != "none")
   action = function() { set_shuffle(true); };
 }
 // Scrobbling - L
 else if (e.which == 108 && !mod) {
  if ($("#scrobbling .scrobbling").css("display") != "none")
   action = function() { set_scrobbling(false); };
  else if ($("#scrobbling .no_scrobbling").css("display") != "none")
   action = function() { set_scrobbling(true); };
 }
 if (typeof(action) == "function") {
  e.preventDefault();
  action();
 }
}

function play_next_song() {
 var el = get_current_song_element();
 var queue = get_queue_el().children("li");
 var next;
 if (shuffle && queue.length > 1) {
  var queue = queue.not(el);
  next = queue.eq(Math.round(Math.random() * (queue.length - 1)));
 } else {
  next = el.next();
  if (next.length == 0) {
   if (repeat)
    next = queue.first();
   else {
    stop_playing();
    return;
   }
  }
 }
 stop_song_only();
 play_history.push(el.attr("id"));
 play_song(next);
}

function play_previous_song() {
 var last_press = previous_button_last_pressed;
 previous_button_last_pressed = $.now();
 if (previous_button_last_pressed - last_press > 1000 &&
     (player.currentTime > PREVIOUS_NO_REPLAY_THRESHOLD ||
      play_history.length == 0)) {
  $player.jPlayer("play", 0);
  scrobbled = false;
  if (get_buffer_percent() == 100)
   update_now_playing(get_current_song_element(), player.duration);
 } else {
  var el = $("#" + play_history[play_history.length - 1]);
  stop_song_only();
  play_history.splice(play_history.length - 1, 1);
  play_song(el);
 }
}

function play_song(el) {
 stop_song_only();
 $("#song_info").attr("data-song-loaded", "false");
 $("#song_info").attr("data-start-time", "");
 $("#song_info .welcome_title").hide();
 $("#song_info .title").show();
 $("#song_info .title").text(el.attr("data-song-title"));
 $("#song_info .title").attr("title", el.attr("data-song-title"));
 $("#song_info .extra .not_playing").hide();
 song_length = Number(el.attr("data-song-length"));
 var extra_tooltip = "";
 var album = el.attr("data-song-album");
 if (album != "" && album != "(Unknown)") {
  $("#song_info .extra .album").show();
  $("#song_info .extra .album .name").text(album);
  extra_tooltip += "from " + album;
 } else
  $("#song_info .extra .album").hide();
 var artist = el.attr("data-song-artist");
 if (artist != "" && artist != "(Unknown)") {
  $("#song_info .extra .artist").show();
  $("#song_info .extra .artist .name").text(artist);
  if (extra_tooltip != "")
   extra_tooltip += " ";
  extra_tooltip += "by " + artist;
 } else
  $("#song_info .extra .artist").hide();
 if (extra_tooltip != "")
  $("#song_info .extra").attr("title", extra_tooltip);
 else
  try {
   $("#song_info .extra").removeAttr("title");
  } catch(e) {}
 $("#song_info").attr("data-song-dom-id", el.attr("id"));
 el.addClass("selected");
 set_icon_url(el, "{{root_url}}/images/play.png");
 var art_url = el.attr("data-song-art-directory") + "/album.png?size=92";
 if ($("#artwork .artwork").attr("src") != art_url) {
  $("#artwork .artwork").replaceWith(
   $("<img />").addClass("artwork").attr("src", "{{root_url}}/images/blank.png")
   .attr("alt", "").hide()
  );
  $("#artwork .generic").show();
  var img = $("<img />").addClass("artwork").attr("src", art_url);
  var timeout = setTimeout(play_song_finish_loading, 3000);
  img.attr("alt", "").load(function() {
   clearTimeout(timeout);
   $(this).click(function() { show_large_artwork(); });
   $("#artwork .generic").hide();
   $("#artwork .artwork").replaceWith($(this).css("display", "inline"));
   if ($("#song_info").attr("data-song-loaded") != "true")
    play_song_finish_loading();
  });
 } else
  play_song_finish_loading();
}

function play_song_finish_loading() {
 var el = get_current_song_element();
 update_prev_next_buttons();
 player_load(el.attr("data-song-url"));
 player_play();
 if (!scrubber_seek.enabled) scrubber_seek.enable();
 $("#song_length").text(time_text(song_length))
 $("#song_info").attr("data-song-loaded", "true");
 $("#song_info").attr("data-start-time", String(Math.round($.now() / 1000)));
}

function player_load(url) {
 $player.jPlayer("setMedia", {mp3: url});
}

function player_pause() {
 player.pause();
}

function player_play() {
 player.play();
}

function player_stop() {
 stop_song_only();
 $("#play_pause .play").hide();
 $("#play_pause .pause").hide();
 $("#play_pause .no_play").show();
}

function player_toggle() {
 if (player.paused)
  player.play();
 else
  player.pause();
}

function process_row(el, callback) {
 if (el.children(".children").html() == "") {
  var category = el.attr("data-category");
  var url = "";
  if (category == "queue") {
   var old_song_dom_id = $("#song_info").attr("data-song-dom-id");
   if (old_song_dom_id != "" && typeof($("#" + old_song_dom_id)) == "object")
    play_history.push(old_song_dom_id);
   stop_song_only();
   play_song(el);
   return
  } else if (category == "album"||category == "playlist"||category == "songs") {
   // 1. replace queue with all songs in category
   queue_push_each(el.parent("ul"), true);
   // 2. play selected song
   play_song($("#queue_" + el.attr("id")));
   return;
  } else {
   url = get_list_url(el, "expand", "json")
  }
  insert_list_from_json_url(url, el.children(".children"), function() {
   el.addClass("expanded");
   if (typeof(callback) == "function")
    callback();
  });
 } else {
  el.children(".children").html("")
  el.removeClass("expanded");
 }
}

function queue_push_each(list_el, replace) {
 var queue_el;
 if (replace == true)
  queue_el = $("<ul></ul>").addClass("queue");
 else
  queue_el = get_queue_el();
 list_el.children("li").each(function() {
  queue_push_one($(this), queue_el);
 });
 if (replace == true) {
  get_queue_el().replaceWith(queue_el);
  play_history = [];
 }
}

function queue_push_one(item_el, queue_el) {
 if (item_el.hasClass("border"))
  return;
 var queue_el = queue_el;
 if (typeof(queue_el) == "undefined")
  queue_el = get_queue_el();
 var new_item = item_el.clone(true).attr("id", "queue_" + item_el.attr("id"));
 new_item.attr("data-category", "queue");
 var row = new_item.children(".table").children(".row");
 row.children(".name").text(new_item.attr("data-full-name"));
 row.children(".add").remove();
 row.children(".remove").css("display", "");
 if (queue_el.children("#" + new_item.attr("id")).length == 0)
  queue_el.append(new_item);
}

function queue_to_xspf() {
 var container = $("<div></div>");
 var xspf = $("<playlist></playlist>").attr("version", "1");
 xspf.attr("xmlns", "http://xspf.org/ns/0/");
 var trackList = $("<trackList></trackList>");
 get_queue_el().children("li").each(function() {
  var t = $("<track></track>");
  t.append($("<location></location>").text($(this).attr("data-song-url")));
  t.append($("<title></title>").text($(this).attr("data-song-title")));
  t.append($("<creator></creator>").text($(this).attr("data-song-artist")));
  t.append($("<annotation></annotation>").text($(this).attr("data-song-album")));
  t.append($("<image></image>").text($(this).attr("data-song-art-url")));
  trackList.append(t);
 });
 xspf.append(trackList);
 container.append(xspf);
 return '<?xml version="1.0" encoding="utf-8"?>\n' + container.html();
}

function remove_from_queue(el) {
 if (get_queue_el().children().length == 1)
  clear_queue();
 else {
  if (el.attr("id") == $("#song_info").attr("data-song-dom-id"))
   play_next_song();
  el.remove();
 }
}

function remove_link_clicked(event) {
 remove_from_queue($(this).parent(".row").parent(".table").parent("li"));
 if ($("#play_pause .no_play").css("display") == "none")
  update_prev_next_buttons();
}

function reset_scrobble_variables() {
 scrobble_threshold = null;
 scrobbled = false;
}

function reset_seek_bar() {
 scrubber_seek.reset()
 scrubber_seek.setAvailablePercent(0);
 $("#time_elapsed, #song_length").text(time_text(0));
}

function row_clicked(event) {
 process_row($(this).parent(".row").parent(".table").parent("li"));
}

function scrobble(el, start_time, duration) {
 if (scrobbling) {
  start_time = Math.round(start_time);
  duration = Math.round(duration);
  timestamp = start_time + duration;
  var id = el.attr("data-id");
  var url = "{{root_url}}/scrobble/" + id + "?timestamp=" + String(timestamp);
  if (typeof(duration) != "undefined")
   url += "&duration=" + String(duration);
  $.get(url);
 }
}

function scrubber_seek_changed(e) {
 var duration = (song_length) ? song_length : player.duration;
 $player.jPlayer("play", duration * e.coefficient);
 if (seek_interval) {
  clearInterval(seek_interval);
  seek_interval = null;
 }
}

function scrubber_volume_changed(e) {
 $player.jPlayer("volume", e.coefficient);
}

function seek_interval_callback() {
 // if buffer is not empty
 if (buffered_percent)
  update_seek_bar(player.currentTime);
}

function set_icon_url(el, icon_url) {
 try {
  if (icon_url == "")
   icon_url = el.attr("data-icon");
  icon_url = icon_url.replace("'", "\\'");
  el.children(".table").children(".row").children(".icon")
   .css("background-image", "url('" + icon_url + "')");
 } catch(e) {}
}

function set_repeat(setting) {
 repeat = setting;
 if (repeat) {
  $("#repeat .no_repeat").hide();
  $("#repeat .repeat").show();
 } else {
  if (shuffle)
   set_shuffle(false);
  $("#repeat .repeat").hide();
  $("#repeat .no_repeat").show();
 }
 update_prev_next_buttons();
}

function set_scrobbling(setting) {
 scrobbling = setting;
 if (scrobbling) {
  $("#scrobbling .no_scrobbling").hide();
  $("#scrobbling .scrobbling").show();
 } else {
  $("#scrobbling .scrobbling").hide();
  $("#scrobbling .no_scrobbling").show();
 }
}

function set_shuffle(setting) {
 shuffle = setting;
 if (shuffle) {
  set_repeat(true);
  $("#shuffle .no_shuffle").hide();
  $("#shuffle .shuffle").show();
 } else {
  $("#shuffle .shuffle").hide();
  $("#shuffle .no_shuffle").show();
 }
}

function show_large_artwork() {
 var large_art_url;
 if ($("#artwork .artwork").css("display") != "none") {
  var el = get_current_song_element();
  large_art_url = el.attr("data-song-art-directory");
 }
 else
  large_art_url = "{{root_url}}/generic-artwork";
 var large_art_size = 500;
 if (Math.floor(Math.round($("#wrapper").height()*0.8)/25)*25 > 0)
  large_art_size = Math.floor(Math.round($("#wrapper").height()*0.8)/25)*25;
 large_art_url += "/album.png?size=" + large_art_size;
 large_art_url = large_art_url.replace("'", "\\'");
 var lightbox = $("<div></div>").attr("id", "large_art_lightbox").hide();
 var image = $("<div></div>").addClass("image");
 image.css("background-image", "url('" + large_art_url + "')");
 lightbox.append(image);
 $("#large_art_lightbox_container").append(lightbox);
 $("#large_art_lightbox, #large_art_lightbox *").click(function() {
  hide_large_artwork();
 });
 lightbox.fadeIn(400);
}

function stop_playing() {
 player_stop();
 $("#song_info").attr("data-song-loaded", "false");
 $("#song_info").attr("data-start-time", "");
 $("#song_info .title").hide();
 $("#song_info .welcome_title").show();
 $("#song_info .extra .artist").hide();
 $("#song_info .extra .album").hide();
 $("#song_info .extra .not_playing").show();
 $("#artwork .artwork").hide();
 $("#artwork .generic").show();
 $("#song_info").attr("data-song-dom-id", "");
}

function stop_song_only() {
 $player.jPlayer("clearMedia");
 buffered_percent = 0;
 song_length = 0;
 reset_seek_bar();
 reset_scrobble_variables();
 unselect_current_song();
 update_prev_next_buttons();
}

function time_text(seconds) {
 seconds = Math.floor(Math.round(seconds));
 var minutes = Math.floor(seconds / 60) % 60;
 var hours = Math.floor(seconds / 3600);
 var text = ("0" + String(seconds % 60)).substr(-2);
 if (hours) {
  text = ("0" + String(minutes)).substr(-2) + ":" + text;
  if (hours)
   text = String(hours) + ":" + text;
 } else
  text = String(minutes) + ":" + text;
 return text;
}

function toggle_mute() {
 player.muted = !player.muted;
 $player.jPlayer("mute", player.muted);
}

function unselect_current_song() {
 hide_large_artwork();
 var previous_dom_id = $("#song_info").attr("data-song-dom-id");
 if (previous_dom_id != "" && typeof($("#" + previous_dom_id)) != "undefined") {
  set_icon_url($("#" + previous_dom_id), "");
  $("#" + previous_dom_id).removeClass("selected");
 }
}

function update_now_playing(el, duration) {
 if (scrobbling) {
  var id = el.attr("data-id");
  var url = "{{root_url}}/update-now-playing/" + id;
  if (typeof(duration) == "number")
   url += "?duration=" + Math.round(duration);
  $.get(url);
 }
}

function update_prev_next_buttons() {
 var prev = [$("#previous .previous"), $("#previous .no_previous")];
 var next = [$("#next .next"), $("#next .no_next")];
 var queue = get_queue_el().children("li");
 if (queue.length == 0) {
  prev[0].hide();
  prev[1].show();
  next[0].hide();
  next[1].show();
 } else if (!repeat && (queue.length == 1 ||
            queue.last().attr("id")==$("#song_info").attr("data-song-dom-id"))){
  prev[1].hide();
  prev[0].show();
  next[0].hide();
  next[1].show();
 } else {
  prev[1].hide();
  prev[0].show();
  next[1].hide();
  next[0].show();
 }
}

function update_seek_bar(position, duration) {
 if (position == null) position = 0;
 if (duration == null) duration = song_length;
 scrubber_seek.moveToCoefficient(position / duration);
 $("#time_elapsed").text(time_text(position));
 if (duration != null)
  $("#song_length").text(time_text(duration));
}

function update_volume_bar(coeff) {
 update_volume_icon();
 scrubber_volume.moveToPercent(coeff * 100);
}

function update_volume_icon(muted) {
 if (muted) {
  $("#volume_button img").hide();
  $("#volume_button .volume_muted").show();
 } else {
  $("#volume_button img").hide()
  var volume = player.volume;
  if (volume > 0.66)
   $("#volume_button .volume_max").show();
  else if (volume > 0.33)
   $("#volume_button .volume_med").show();
  else if (volume)
   $("#volume_button .volume_min").show();
  else
   $("#volume_button .volume_zero").show();
 }
}
