# -*- coding: UTF-8 -*-
"""
Othman - Quran browser
gtkUi - gtk user interface for Othman API

Copyright © 2008-2010, Muayyad Alsadi <alsadi@ojuba.org>

        Released under terms of Waqf Public License.
        This program is free software; you can redistribute it and/or modify
        it under the terms of the latest version Waqf Public License as
        published by Ojuba.org.

        This program is distributed in the hope that it will be useful,
        but WITHOUT ANY WARRANTY; without even the implied warranty of
        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

        The Latest version of the license can be found on
        "http://waqf.ojuba.org/license"

"""
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
import sys, os, os.path, time
import gettext
import json
from gi.repository import Gtk, Gdk, GLib, Pango, GdkPixbuf,Gst,GObject,Gio
from .core import othmanCore, searchIndexer
import threading
import zipfile
import sqlite3
import re

Gst.init(None)

PY2 = sys.version_info[0]==2
BYTE = str if PY2 else bytes

class searchWindow(Gtk.Window):
    def __init__(self, w):
        Gtk.Window.__init__(self)
        self.w = w
        self.connect('delete-event', lambda w,*a: w.hide() or True)
        self.last_txt = None
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.set_modal(True)
        self.set_deletable(True)
        self.set_title(_('Search results'))
        self.set_transient_for(w)
        vb = Gtk.VBox(False,0)
        self.add(vb)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT )
        
        self.search = Gtk.Entry()
        self.search.set_width_chars(15)
        vb.pack_start(self.search, False,False, 0)
        
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.AUTOMATIC,Gtk.PolicyType.AUTOMATIC)
        self.scroll.set_size_request(100, 250)
        vb.pack_start(self.scroll,True, True, 6)
        
        self.ls = Gtk.ListStore(int,str,int,int)
        self.cells = []
        self.cols = []
        self.cells.append(Gtk.CellRendererText())
        self.cols.append(Gtk.TreeViewColumn(_('Sura'), self.cells[0], text=1))
        self.cols[0].set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        self.cols[0].set_resizable(True)

        self.cells.append(Gtk.CellRendererText()); # self.cols[-1].set_expand(False)
        self.ls_w = Gtk.TreeView(self.ls)
        self.ls_w.connect("cursor-changed", self.move)
        self.ls_w.set_direction(Gtk.TextDirection.RTL)
        self.ls_w.set_headers_visible(False)
        for i in self.cols:
            self.ls_w.insert_column(i, -1)
        self.scroll.add(self.ls_w)
        self.search.connect("activate", self.search_cb)
        self.show_all()
        self.connect("key-press-event", self._on_key_press)

    def _on_key_press(self,widget, event):
        if event.keyval == Gdk.KEY_Escape :
            self.hide()
            
    def move(self, t):
        a = self.ls_w.get_selection().get_selected()
        if not a or len(a) < 2 or not a[1]:
            return
        sa = self.ls[self.ls.get_path(a[1])]
        self.w.sura_c.set_active(sa[2]-1)
        self.w.viewAya(sa[3], sa[2])

    def search_cb(self, b, *a):
        t = b.get_text()
        self.w.search.set_text(t)
        self.find(t)

    def find(self, txt, backward = False):
        txt = txt.strip()
        if not txt:
            self.hide()
            return
        if type(txt) == BYTE:
            txt = txt.decode('utf-8')
        if txt == self.last_txt:
            # TODO: just move cursor to next/prev result before showing it
            pass
        else:
            self.search.set_text(txt)
            self.last_txt = txt
            self.ls.clear()
            for i in self.w.ix.findPartial(txt.split()):
                sura, aya = self.w.suraAyaFromAyaId(i)
                name = self.w.suraInfoById[sura-1][0]
                self.ls.append([i, "%03d %s - %03d" % (sura, name, aya), sura, aya,])
            self.ls_w.set_cursor(Gtk.TreePath(path=0), None, False)
        self.show_all()

###############################################################################

class ShowTarajemTafasir(Gtk.Window):
    def __init__(self, w=None,tafasir_data_location=None,tooltip="",add_title="",title_="",sura_n=1,aya_n=1,sura="",aya="",msg_if_faild = "",all_audio=None,istarajem=True):
        Gtk.Window.__init__(self)
        self.suwar_info = {'1': '7', '2': '286', '3': '200', '4': '176', '5': '120', '6': '165', '7': '206', '8': '75', '9': '129', '10': '109', 
                           '11': '123', '12': '111', '13': '43', '14': '52', '15': '99', '16': '128', '17': '111', '18': '110', '19': '98', 
                            '20': '135', '21': '112', '22': '78', '23': '118', '24': '64', '25': '77', '26': '227', '27': '93', '28': '88', 
                            '29': '69', '30': '60', '31': '34', '32': '30', '33': '73', '34': '54', '35': '45', '36': '83', '37': '182', 
                            '38': '88', '39': '75', '40': '85', '41': '54', '42': '53', '43': '89', '44': '59', '45': '37', '46': '35', 
                            '47': '38', '48': '29', '49': '18', '50': '45', '51': '60', '52': '49', '53': '62', '54': '55', '55': '78', 
                            '56': '96', '57': '29', '58': '22', '59': '24', '60': '13', '61': '14', '62': '11', '63': '11', '64': '18', 
                            '65': '12', '66': '12', '67': '30', '68': '52', '69': '52', '70': '44', '71': '28', '72': '28', '73': '20', 
                            '74': '56', '75': '40', '76': '31', '77': '50', '78': '40', '79': '46', '80': '42', '81': '29', '82': '19', 
                            '83': '36', '84': '25', '85': '22', '86': '17', '87': '19', '88': '26', '89': '30', '90': '20', '91': '15', 
                            '92': '21', '93': '11', '94': '8', '95': '8', '96': '19', '97': '5', '98': '8', '99': '8', '100': '11', '101': '11', 
                            '102': '8', '103': '3', '104': '9', '105': '5', '106': '4', '107': '7', '108': '3', '109': '6', '110': '3', '111': '5', 
                            '112': '4', '113': '5', '114': '5'}
        self.w            = w
        self.tafasir_data_location = tafasir_data_location
        self.tooltip      = tooltip
        self.add_title    = add_title
        self.sura_n       = sura_n
        self.aya_n        = aya_n
        self.sura         = sura
        self.aya          = aya
        self.msg_if_faild = msg_if_faild
        self.title_       = title_
        self.__all_audio  = all_audio
        self.istarajem    = istarajem
        self.cleanr       = re.compile('<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});')
        self.set_size_request(600, 400)
        self.max_sura_number = self.suwar_info[str(self.sura_n)]
        self.pipeline = Gst.ElementFactory.make("playbin", "player")
        
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT )

        self.w.set_sensitive(False)
        self.set_deletable(True)
        self.set_title(self.title_)
        
        self.header=Gtk.HeaderBar()
        self.header.set_show_close_button(True)
        self.headerhbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.header.pack_start(self.headerhbox)
        self.set_titlebar(self.header)
        img = Gtk.Image.new_from_icon_name("list-add-symbolic", Gtk.IconSize.BUTTON)
        self.add_tafasir = Gtk.Button()
        self.add_tafasir.set_tooltip_text(self.tooltip)
        self.add_tafasir.add(img)
        self.headerhbox.pack_start(self.add_tafasir, False, False, 0)
        self.add_tafasir.connect("clicked", self._on_add_tafasir_clicked)
        
        self.maincontainer = Gtk.VBox()
        self.add(self.maincontainer)
        self.connect("key-press-event", self._on_key_press)
        self.connect('delete-event', self._on_delete_event)
        self.__all_tafasir = self.get_all_tafasir_location()
        self.othmancore = othmanCore()
        self.gui_()

    def _stop_audio(self,button=False):
        self.pipeline.set_state(Gst.State.NULL)

    def _play_audio(self,button=False):
        self._stop_audio()
        aya   = self.aya_n
        sura  = self.sura_n
        aya_  = str(aya)
        sura_ = str(sura)
        q = self.__all_audio[self.audio_c.get_active_text()]

        if aya==0 and sura not in (9,1) :
            q = os.path.join(q,"001001.mp3")
        else:
            s_ = ("0"*(3-len(sura_)))+sura_
            a_ = ("0"*(3-len(aya_)))+aya_
            #q = os.path.join(q,sura_.zfill(4-len(sura_))+aya_.zfill(4-len(aya_))+".mp3")
            q = os.path.join(q,s_+a_+".mp3")
        if not os.path.isfile(q):
            return
        
        if  sys.platform.startswith('win'):
            q =  "file:///"+os.path.abspath(q).replace(os.sep, '/')
        else:
            q = "file://"+os.path.abspath(q)

        self.pipeline.set_property('uri',q)
        self.pipeline.set_state(Gst.State.PLAYING)

        
    def _on_key_press(self,widget, event):
        print(event.keyval)
        if  event.keyval == Gdk.KEY_Left  :
            self.rewind_b.emit("clicked",self.entry,self.entry_handler)
                
        elif   event.keyval == Gdk.KEY_Right  :
            self.forward_b.emit("clicked",self.entry,self.entry_handler)
        self.queue_draw()

    def _on_add_tafasir_clicked(self,button):
        self.add_w = AddData(self,self.tafasir_data_location,self.add_title)
        self.add_w.set_title(self.add_title)
        self.add_w.connect("success",self._on_add_tafasir_success)
        
    def _on_add_tafasir_success(self,w=None):
        self.__all_tafasir = self.get_all_tafasir_location()
        self.add_w.destroy()
        self.gui_()
        #width , height = self.get_size()
        #self.add_w.destroy()
        #self.destroy()
        #s_ = ShowTarajemTafasir(self.w,self.tafasir_data_location,self.tooltip,self.add_title,self.title_,self.sura_n,self.aya_n,self.sura,self.aya,self.msg_if_faild)
        #s_.resize(width , height)

    def get_all_tafasir_location(self):
        result = {}
        if not os.path.isdir(self.tafasir_data_location):
            return False
        for dirname,folder,files in os.walk(self.tafasir_data_location):
            for file_ in files:
                if file_.endswith(".db") or file_.endswith(".ayt") or file_.endswith(".sqlite"):
                    result.setdefault(file_.split(".",1)[0],os.path.join(dirname,file_))
        if result:
            return result
        return False

    def on_back_aya(self,button,entry,entry_handler):
        listboxrow = self.listbox_ .get_selected_row()
        if not listboxrow:
            return
        if self.aya_n-1==0:
            return
        self.aya_n-=1
        with GObject.Object.handler_block(entry,entry_handler):
            entry.set_text(str(self.aya_n))
        self.aya = self.othmancore.getAyatIter(self.othmancore.ayaIdFromSuraAya(self.sura_n,self.aya_n)).fetchall()[0][0]
        t  = listboxrow.get_child().props.label
        db = self.__all_tafasir[t]
        self.aya_info(db,t)
        
    def on_forward_aya(self,button,entry,entry_handler):
        listboxrow = self.listbox_ .get_selected_row()
        if not listboxrow:
            return
        if self.aya_n+1>int(self.max_sura_number):
            return
        self.aya_n+=1
        with GObject.Object.handler_block(entry,entry_handler):
            entry.set_text(str(self.aya_n))
        self.aya = self.othmancore.getAyatIter(self.othmancore.ayaIdFromSuraAya(self.sura_n,self.aya_n)).fetchall()[0][0]
        t  = listboxrow.get_child().props.label
        db = self.__all_tafasir[t]
        self.aya_info(db,t)

    def on_entry_activate(self,entry):
        text = entry.get_text()
        listboxrow = self.listbox_.get_selected_row()
        if not listboxrow:
            return
        try:
            it = int(text)
        except:
            return
        if it>int(self.max_sura_number) or it==0:
            return
        else:
            self.aya_n = it
            self.aya = self.othmancore.getAyatIter(self.othmancore.ayaIdFromSuraAya(self.sura_n,self.aya_n)).fetchall()[0][0]
            t  = listboxrow.get_child().props.label
            db = self.__all_tafasir[t]
            self.aya_info(db,t)
            
    def gui_(self):
        self.remove(self.maincontainer)
        self.maincontainer.destroy()
        self.maincontainer = Gtk.HBox()
        self.add(self.maincontainer)
        if self.sura_n not in (1,9) and self.aya_n==0:
            self.aya_n=1
        if  self.__all_tafasir:
            self.connect("key-press-event", self._on_key_press)#########################


            hb = Gtk.HBox()
            hb.set_spacing(2)
            hb.pack_start(Gtk.VSeparator(), False, False, 6)
            hb.pack_start(Gtk.Label(_("Audio")), False, False, 0)
            self.audio_c = Gtk.ComboBoxText.new()
            self.audio_c.set_wrap_width(5)
            if self.__all_audio:
                for i in self.__all_audio.keys():
                    self.audio_c.append_text(i)
                self.audio_c.set_tooltip_text(_("choose a Audio"))
                self.audio_c.set_active(0)
            else:
                self.audio_c.set_sensitive(False)
                self.audio_c.set_tooltip_text(_("No Audio Available"))
            hb.pack_start(self.audio_c, False, False, 0)
        
            audiohb = Gtk.HBox()
            audiohb.set_spacing(2)
            img = Gtk.Image.new_from_icon_name("media-playback-start", Gtk.IconSize.BUTTON)
            self.play_b = Gtk.Button()
            self.play_b.set_tooltip_text(_("Play"))
            self.play_b.add(img)
            audiohb.pack_start(self.play_b, False, False, 0)
            self.play_b.connect("clicked", self._play_audio)
        
            img = Gtk.Image.new_from_icon_name("media-playback-stop", Gtk.IconSize.BUTTON)
            self.stop_b = Gtk.Button()
            self.stop_b.set_tooltip_text(_("Stop"))
            self.stop_b.add(img)
            audiohb.pack_start(self.stop_b, False, False, 0)
            self.stop_b.connect("clicked", self._stop_audio)
            
            if not self.__all_audio:
                self.play_b.set_sensitive(False)
                self.stop_b.set_sensitive(False)

            
            self.header.pack_start(hb)
            self.header.pack_start(audiohb)
        
            h = Gtk.HBox()
            h.props.spacing = 10
            self.entry = Gtk.Entry()
            self.entry.set_max_width_chars(3)
            self.entry.set_input_purpose(Gtk.InputPurpose.DIGITS)
            self.entry.set_text(str(self.aya_n))
            self.entry_handler = self.entry.connect("activate",self.on_entry_activate)
            label_aya_number = Gtk.Label()
            label_aya_number.props.label = "/{}".format(self.max_sura_number)
    
            img = Gtk.Image.new_from_icon_name("media-seek-backward", Gtk.IconSize.BUTTON)
            self.rewind_b = Gtk.Button()
            self.rewind_b.add(img)
            h.pack_start(self.rewind_b, False, False, 0)
            self.rewind_b.connect("clicked", self.on_back_aya,self.entry,self.entry_handler)

            h.pack_start(self.entry, False, False, 0)
            h.pack_start(label_aya_number, False, False, 0)
            
            img = Gtk.Image.new_from_icon_name("media-seek-forward", Gtk.IconSize.BUTTON)
            self.forward_b = Gtk.Button()
            self.forward_b.add(img)
            h.pack_start(self.forward_b, False, False, 0)
            self.forward_b.connect("clicked", self.on_forward_aya,self.entry,self.entry_handler)
            
            self.header.pack_end(h)
            sw1=Gtk.ScrolledWindow()
            sw1.set_policy(Gtk.PolicyType.AUTOMATIC,Gtk.PolicyType.AUTOMATIC)
            sw2=Gtk.ScrolledWindow()
            sw2.set_policy(Gtk.PolicyType.AUTOMATIC,Gtk.PolicyType.AUTOMATIC)
            
            sw1.set_size_request (150, 1)
            self.maincontainer.pack_start(sw1,False,False,0)
            self.maincontainer.pack_start(sw2,True,True,0)
            

            self.listbox_ = Gtk.ListBox()
            sw1.add(self.listbox_)
            self.__check = True

            self.text_v = Gtk.TextView()
            self.text_v.set_hexpand(True)
            self.text_v.set_vexpand(True)
            self.text_v.props.editable = False
            self.text_v.props.cursor_visible = False
            self.text_v.props.justification = Gtk.Justification.CENTER
            self.text_v.props.wrap_mode = Gtk.WrapMode.WORD
            self.buffer = self.text_v.get_buffer()
            sw2.add(self.text_v)
            
            if self.istarajem :
                cc = self.w._current_tarajem
            else:
                cc = self.w._current_tafasir
            for category in dict(sorted(self.__all_tafasir.items())).keys():
                category_label = Gtk.Label()
                category_label.set_label(category)
                row_ = Gtk.ListBoxRow()
                row_.props.activatable = True
                row_.props.selectable = True
                row_.add(category_label)
                self.listbox_.add(row_)
                if category==cc:
                    self.listbox_.select_row(row_)

            self.listbox_.connect("row-selected",self.on_selected_row)
            if not cc:
                self.listbox_.select_row(self.listbox_.get_row_at_index(0))
            
        else:
            l = Gtk.Label()
            l.props.label = self.msg_if_faild
            self.maincontainer.add(l)
        

        
        self.show_all()
        
    def on_selected_row(self, listbox,listboxrow):
        t  = listboxrow.get_child().props.label
        db = self.__all_tafasir[t]
        self.aya_info(db,t)
        if self.istarajem :
            self.w._current_tarajem = t
        else:
            self.w._current_tafasir = t

        
    def _on_delete_event(self,*argv):
        self.w.set_sensitive(True)
        self._stop_audio()
        self.destroy()
        
    def _on_key_press(self,widget, event):
        if event.keyval == Gdk.KEY_Escape :
            self.w.set_sensitive(True)
            self._stop_audio()
            self.destroy()
            
    def in_text(self,line,end="\n\n"):
        line = line+end
        self.buffer.insert_markup(self.buffer.get_end_iter(),line,-1)


    def clear_text(self):
        start = self.buffer.get_start_iter()
        end = self.buffer.get_end_iter()
        self.buffer.delete(start, end)

    def aya_info(self,db,table,text="text"):
        self.clear_text()
        try:
            conn = sqlite3.connect(db)
            c = conn.cursor()
            c.execute('SELECT {} FROM {} where sura=? and aya=? ;'.format(text,table),(self.sura_n,self.aya_n))
            rows = c.fetchall()
            if rows:
                self.in_text("<span foreground='blue' size='x-large' weight='bold'>{}</span>".format(self.sura))
                self.in_text("<span foreground='red' size='large' weight='bold'>{}</span>".format(self.aya))
                row = rows[0]
                if row:
                    txt = re.sub(self.cleanr, '', row[0].replace("<br>","\n"))
                    self.in_text("<span foreground='green' size='x-large'>{}</span>".format(txt))
                    #self.show_all()
                    self.__check = True
        except sqlite3.OperationalError:
            if self.__check:
                self.__check = False
                return self.aya_info(db,table,"tafsir")
            else:
                pass
        except Exception as e:
            print(e)
            return False
        finally :
            if conn:
                conn.close()
                
class UnpackZip(threading.Thread):
    def __init__(self,sources_location,target_location,spinner,parent):
        threading.Thread.__init__(self)
        self.sources_location = sources_location
        self.target_location  = target_location
        self.spinner          = spinner
        self.parent           = parent
        self.daemon           = True

    def run(self):
        GLib.idle_add(self.spinner.start)
        GLib.idle_add(self.parent.set_sensitive,False)
        result = []
        for source_location in self.sources_location:
            result.append(self.unpack_file(source_location))

        if any(result):
            GLib.idle_add(self.parent.emit,"success")
            
        GLib.idle_add(self.spinner.stop)
        GLib.idle_add(self.parent.set_sensitive,True)

    def unpack_file(self,source_location):
        if source_location.endswith('.ayt'):
            fun, mode = zipfile.ZipFile, 'r'
        else:
            return False
        #cwd = getcwd()
        #chdir(os.path.dirname(self.source_location))
        try:
            file_ = fun(source_location, mode)
            try:
                file_.extractall(self.target_location)
            except:
                #os.chdir(cwd)
                return False
            finally:
                file_.close()
                
        except:
            #os.chdir(cwd)
            return False
        #finally:
            #os.chdir(cwd)
        return True
                
class AddData(Gtk.Window):
    __gsignals__ = {
        "success"     : (GObject.SignalFlags.RUN_LAST, None, ()),
    }
    
    def __init__(self, w=None,audio_data_location="",msg=""):
        Gtk.Window.__init__(self)
        self.w = w
        self.audio_data_location = audio_data_location
        self.set_size_request(600, 400)
        self.__files = []
        self.msg = msg
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT )
        css = b"""
                .h1 {
                    font-size: 24px;
                }
                .h2 {
                    font-weight: 300;
                    font-size: 18px;
                }
                .h3 {
                    font-size: 11px;
                }
                .h4 {
                    color: alpha (@text_color, 0.7);
                    font-weight: bold;
                    text-shadow: 0 1px @text_shadow_color;
                }
                .h4 {
                    padding-bottom: 6px;
                    padding-top: 6px;
                }
                """
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), style_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        
        self.connect('delete-event', self._on_cancel_button_clicked)
        self.last_txt = None
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.set_modal(True)
        self.set_deletable(True)
        self.set_transient_for(w)
        vb = Gtk.VBox()
        hb = Gtk.HBox()
        
        linkbutton = Gtk.LinkButton.new_with_label("http://quran.ksu.edu.sa/ayat/?l=ar&pg=patches","http://quran.ksu.edu.sa")
        
        label      = Gtk.Label()
        label.get_style_context().add_class("h2")
        label.set_label(self.msg)
        self.fvbox = Gtk.VBox(spacing=10)
        self.svbox = Gtk.VBox(spacing=10)
        self.fvbox.set_homogeneous(True)
        self.svbox.set_homogeneous(True)
        self.spinner  = Gtk.Spinner()
        
        
        self.choicefile_label = Gtk.Label()
        self.choicefile_label.get_style_context().add_class("h2")
        self.choicefile_label.set_label(_("Select ayt File"))
        self.choicefile_b = Gtk.Button()
        self.choicefile_b.props.label = _("Choose Files")
        self.choicefile_b.connect("clicked",self.on_file_button_clicked)
        

        self.fvbox.pack_start(self.choicefile_label,False,False,0)
        self.svbox.pack_start(self.choicefile_b,False,False,0)


        self.open_audio_location_button = Gtk.Button()
        self.open_audio_location_button.props.label = _("Open Data Location")
        self.open_audio_location_button.connect("clicked",self.on_open_data_location_button_clicked)
        
        buttonbox = Gtk.HBox()        
        cansel_button = Gtk.Button()
        cansel_button.props.label = _("Cancel")
        cansel_button.connect("clicked",self._on_cancel_button_clicked)
        
        buttonbox.pack_start(self.open_audio_location_button,True,False,0)
        buttonbox.pack_start(cansel_button,True,False,0)
        
        vb.pack_start(linkbutton,True,False,0)
        vb.pack_start(label,True,False,0)
        hb.pack_start(self.fvbox,True,False,0)
        hb.pack_start(self.svbox,True,False,0)
        vb.pack_start(hb,True,False,0)
        vb.pack_start(self.spinner,True,False,0)
        vb.pack_start(buttonbox,True,False,0)
        
        
        self.add(vb)
        self.show_all()

    def on_file_button_clicked(self, button):
        self.__files.clear()
        dialog = Gtk.FileChooserDialog(_("Please choose a files"), self,
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        
        ayt_filter = Gtk.FileFilter.new()
        zip_filter = Gtk.FileFilter.new()
        ayt_filter.set_name("Ayt file")
        zip_filter.set_name("zip file")
        ayt_filter.add_pattern("*ayt")
        zip_filter.add_mime_type("application/zip")
        dialog.add_filter(ayt_filter)
        dialog.add_filter(zip_filter)
        dialog.set_select_multiple(True)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self._files =  dialog.get_filenames()
            dialog.destroy()
            self.run_ex_zip()
        else:
            dialog.destroy()
        
    def on_open_data_location_button_clicked(self,button):
        if  sys.platform.startswith('win'):
            os.system("explorer {}".format(self.audio_data_location))
        else:
            try:
                Gio.AppInfo.launch_default_for_uri(("file:///"+self.audio_data_location),None)
            except Exception as e:
                print(e)
        
    def run_ex_zip(self):
        if self._files:
            u_ = UnpackZip(self._files,self.audio_data_location,self.spinner,self)
            u_.start()

    def _on_cancel_button_clicked(self,*argv):
        self.destroy()
        
class Yes_Or_No(Gtk.MessageDialog):
    def __init__(self,msg,parent=None,link_button="https://www.amirifont.org"):
        Gtk.MessageDialog.__init__(self,buttons = Gtk.ButtonsType.YES_NO )
        self.props.message_type = Gtk.MessageType.QUESTION
        self.props.text         = msg
        self.p=parent
        self.link_button        = link_button
        if self.p != None:
            self.parent=self.p
            self.set_transient_for(self.p)
            self.set_modal(True)
            self.p.set_sensitive(False)
        else:
            self.set_position(Gtk.WindowPosition.CENTER)
        if self.link_button:
            linkbutton = Gtk.LinkButton.new(self.link_button)
            ma = self.get_message_area()
            ma.pack_start(linkbutton,True,True,0)
        self.show_all()
    def check(self):
        rrun = self.run()
        if rrun == Gtk.ResponseType.OK:
            self.destroy()
            if self.p != None:
                self.p.set_sensitive(True)
            return True
        else:
            if self.p != None:
                self.p.set_sensitive(True)
            self.destroy()
            return False
            
class NInfo(Gtk.MessageDialog):
    def __init__(self,message,parent=None):
        Gtk.MessageDialog.__init__(self,parent,1,Gtk.MessageType.INFO,Gtk.ButtonsType.OK,message)
        self.parent=parent
        if self.parent != None:
            self.set_transient_for(self.parent)
            self.set_modal(True)
            self.parent.set_sensitive(False)
        else:
            self.set_position(Gtk.WindowPosition.CENTER)
            
    def start(self):
        self.run() 
        if self.parent != None:
            self.parent.set_sensitive(True)
        self.destroy()
        return False
        
def get_correct_path(relative_path):
    if getattr(sys, 'frozen',False) and hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)
    
def check_amiri_font(window):
    context = window.get_pango_context()
    for fam in context.list_families():
        font_name = fam.get_name().lower()
        if font_name.strip()== "amiri" :
            return True
    return False
###############################################################################

class othmanUi(Gtk.Window, othmanCore):
    def __init__(self,othman_data):
        Gtk.Window.set_default_icon_name('Othman')
        Gtk.Window.__init__(self)
        othmanCore.__init__(self)
        
        ############################
        self.__can_play = True
        self.__isfullscreen = False
        self._current_tafasir = ""
        self._current_tarajem = ""
        self.pipeline = Gst.ElementFactory.make("playbin", "player")
        self.pipeline2 = Gst.ElementFactory.make("playbin", "player")
        self.__bus1 = self.pipeline.get_bus()
        self.__bus1.add_signal_watch()
        self.__bus1.connect("message", self.__on_message,True)
        self.__bus2 = self.pipeline2.get_bus()
        self.__bus2.add_signal_watch()
        self.__bus2.connect("message", self.__on_message)
        self.othman_data = othman_data
        self.audio_data_location = os.path.join(self.othman_data,"ayat_audio")
        os.makedirs(self.audio_data_location,exist_ok=True)
        self.tarajem_data_location = os.path.join(self.othman_data,"ayat_tarajem")
        os.makedirs(self.tarajem_data_location,exist_ok=True)
        self.tafasir_data_location = os.path.join(self.othman_data,"ayat_tafasir")
        os.makedirs(self.tafasir_data_location,exist_ok=True)
 
        
        #style_provider = Gtk.CssProvider()
        #style_provider.load_from_data(css)
        #Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), style_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        
        if  sys.platform.startswith('win'):
            if not check_amiri_font(self):
                y_or_n = Yes_Or_No(_("Amiri Font Missing!,install amiri font?"),self)
                if y_or_n.check():
                    os.system("cmd /C fontview.exe {}".format(get_correct_path("amiri_font\\Amiri-Regular.ttf")))
                    ninfo_ = NInfo(_("Re-run othman"))
                    ninfo_.start()
                    sys.exit()
                else:
                    sys.exit()
        ############################
        
        self.sw = None
        self.lastSearchText = None
        self.lastSearchResult = []
        self.ix = searchIndexer()
        self.set_title(_('Othman Quran Browser'))
        self.connect("delete_event", self.quit)
        self.connect('destroy', self.quit)
        self.set_default_size(600, 480)
        self.maximize()
        self.clip1 = Gtk.Clipboard.get(Gdk.SELECTION_PRIMARY)
        self.clip2 = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.accel = Gtk.AccelGroup()

        vb = Gtk.VBox(False,0)
        self.add(vb)
        hb = Gtk.HBox(False,2)
        vb.pack_start(hb, False, False, 0)

        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.ALWAYS)
        self.scroll.connect_after("size-allocate", self.resize_cb)
        vb.pack_start(self.scroll, True, True, 6)

        img = Gtk.Image()
        img.set_from_stock(Gtk.STOCK_COPY, Gtk.IconSize.BUTTON)
        self.cp_b = Gtk.Button()
        self.cp_b.set_tooltip_text(_("Copy To Clipboard"))
        self.cp_b .add(img)
        self.cp_b .connect("clicked", self.show_cp_dlg)
        hb.pack_start(self.cp_b ,False, False, 0)
        hb.pack_start(Gtk.VSeparator(), False, False, 6)
        hb.pack_start(Gtk.Label(_("Sura")), False, False, 0)

        self.sura_ls = tuple("%d. %s" % (i+1,j[0]) for (i,j) in enumerate(self.suraInfoById))
        self.sura_c = Gtk.ComboBoxText.new()
        self.sura_c.set_wrap_width(5)
        for i in self.sura_ls:
            self.sura_c.append_text(i)
        self.sura_c.set_tooltip_text(_("choose a Sura"))
        self.sura_c.connect("changed", self.sura_changed_cb)
        hb.pack_start(self.sura_c, False, False, 0)


        ##############################################################
        hb.pack_start(Gtk.VSeparator(), False, False, 6)
        hb.pack_start(Gtk.Label(_("Audio")), False, False, 0)
        self.__all_audio = self.get_all_audio_location()
        self.audio_c = Gtk.ComboBoxText.new()
        self.audio_c.set_wrap_width(5)
        if self.__all_audio:
            for i in self.__all_audio.keys():
                self.audio_c.append_text(i)
            self.audio_c.set_tooltip_text(_("choose a Audio"))
            self.audio_c.set_active(0)
        else:
            self.audio_c.set_sensitive(False)
            self.audio_c.set_tooltip_text(_("No Audio Available"))
        hb.pack_start(self.audio_c, False, False, 0)

        audiohb = Gtk.HBox()
        audiohb.set_spacing(2)
        img = Gtk.Image.new_from_icon_name("media-seek-backward", Gtk.IconSize.BUTTON)
        self.rewind_b = Gtk.Button()
        self.rewind_b.set_tooltip_text(_("Seek Audio Previous"))
        self.rewind_b.add(img)
        audiohb.pack_start(self.rewind_b, False, False, 0)
        self.rewind_b.connect("clicked", self.seek_audio,False)
        
        
        
        img = Gtk.Image.new_from_icon_name("media-playback-start", Gtk.IconSize.BUTTON)
        self.play_b = Gtk.Button()
        self.play_b.set_tooltip_text(_("Play"))
        self.play_b.add(img)
        audiohb.pack_start(self.play_b, False, False, 0)
        self.play_b.connect("clicked", self._play_audio)

        img = Gtk.Image.new_from_icon_name("media-seek-forward", Gtk.IconSize.BUTTON)
        self.forward_b = Gtk.Button()
        self.forward_b.set_tooltip_text(_("Seek Audio Forward"))
        self.forward_b.add(img)
        audiohb.pack_start(self.forward_b, False, False, 0)
        self.forward_b.connect("clicked", self.seek_audio)
        
        img = Gtk.Image.new_from_icon_name("media-playback-stop", Gtk.IconSize.BUTTON)
        self.stop_b = Gtk.Button()
        self.stop_b.set_tooltip_text(_("Stop"))
        self.stop_b.add(img)
        audiohb.pack_start(self.stop_b, False, False, 0)
        self.stop_b.connect("clicked", self._stop_audio)
        if not self.__all_audio:
            self.play_b.set_sensitive(False)
            self.stop_b.set_sensitive(False)
            self.rewind_b.set_sensitive(False)
            self.forward_b.set_sensitive(False)
        hb.pack_start(audiohb, False, False, 10)
        
        img = Gtk.Image.new_from_icon_name("list-add-symbolic", Gtk.IconSize.BUTTON)
        self.add_tilawa = Gtk.Button()
        self.add_tilawa.set_tooltip_text(_("Add Audio Sources"))
        self.add_tilawa.add(img)
        hb.pack_start(self.add_tilawa, False, False, 0)
        self.add_tilawa.connect("clicked", self._on_add_tilawa_clicked)
        ###############################################################
        
        
        
        hb.pack_start(Gtk.VSeparator(),False, False, 6)
        img = Gtk.Image()
        img.set_from_stock(Gtk.STOCK_ZOOM_IN, Gtk.IconSize.BUTTON)
        b = Gtk.Button()
        b.set_tooltip_text(_("Zoom In"))
        b.add(img)
        hb.pack_start(b, False, False, 0)
        b.connect("clicked", self.zoomIn)
        
        img = Gtk.Image()
        img.set_from_stock(Gtk.STOCK_ZOOM_OUT, Gtk.IconSize.BUTTON)
        b = Gtk.Button()
        b.set_tooltip_text(_("Zoom Out"))
        b.add(img)
        hb.pack_start(b, False, False, 0)
        b.connect("clicked", self.zoomOut)

        srhbox = Gtk.HBox()
        srhbox.set_spacing(1)
        hb.pack_start(srhbox , False, False, 5)
        
        img = Gtk.Image.new_from_icon_name("go-up-symbolic", Gtk.IconSize.BUTTON)
        b = Gtk.Button()
        b.set_tooltip_text(_("Speed Up Auto Scroll"))
        b.add(img)
        b.connect("clicked", self.speed_up)
        srhbox.pack_start(b , False, False, 0)
        
        
        self.__count = 0
        self.scroll_delay = 200
        img = Gtk.Image.new_from_icon_name("media-playlist-repeat-symbolic", Gtk.IconSize.BUTTON)
        self.tb = Gtk.ToggleButton()
        self.tb.set_tooltip_text(_("Auto Scroll"))
        self.tb.add(img)
        srhbox.pack_start(self.tb , False, False, 0)
        self.autoScrolling = False
        self.tb.connect("clicked", self.autoScrollCb)
        self.source_id = GLib.timeout_add(self.scroll_delay, self.autoScroll, self.tb )
        
        
        img = Gtk.Image.new_from_icon_name("go-down-symbolic", Gtk.IconSize.BUTTON)
        b = Gtk.Button()
        b.set_tooltip_text(_("Speed Down Auto Scroll"))
        b.add(img)
        b.connect("clicked", self.speed_down)
        srhbox.pack_start(b , False, False, 0)

        hb.pack_start(Gtk.VSeparator(), False, False, 6)
        hb.pack_start(Gtk.Image.new_from_stock(Gtk.STOCK_FIND, Gtk.IconSize.BUTTON), False, False, 0)
        search = Gtk.Entry(); search.set_width_chars(15)
        search.set_tooltip_text(_("Search"))
        hb.pack_start(search, False,False, 0)
        search.connect("activate", self.search_cb)
        self.search = search

        hb.pack_start(Gtk.VSeparator(),False, False, 6)
        img = Gtk.Image()
        img.set_from_stock(Gtk.STOCK_ABOUT, Gtk.IconSize.BUTTON)
        b = Gtk.Button()
        b.set_tooltip_text(_("About"))
        b.add(img)
        hb.pack_start(b, False, False, 0)
        b.connect("clicked", lambda *a: self.show_about_dlg(self))


        ############################
        defaultsettings = Gtk.Settings.get_default()
        self.darkmode_switch = Gtk.Switch()
        self.darkmode_switch.set_tooltip_text(_("Dark Mode"))
        self.darkmode_switch.connect("state_set",self._on_darkmode_switch_state_changed,defaultsettings)
        self.darkmode_switch.props.active = defaultsettings.props.gtk_application_prefer_dark_theme
        hb.pack_start(Gtk.VSeparator(),False, False, 6)
        hb.pack_start(self.darkmode_switch,False, False, 6)
        
        self.color_button_bg = Gtk.ColorButton.new_with_color(Gdk.Color.parse("#fffff8")[-1])
        self.color_button_bg.set_tooltip_text(_("Background Color"))
        self.color_button_fg = Gtk.ColorButton.new_with_color(Gdk.Color.parse("#204000")[-1])
        self.color_button_fg.set_tooltip_text(_("Foreground Color"))
        self.color_button_bg.connect("color_set",self._on_color_set)
        self.color_button_fg.connect("color_set",self._on_color_set,False)
        #hb.pack_start(Gtk.VSeparator(),False, False, 6)
        #hb.pack_start(self.color_button_bg,False, False, 6)
        #hb.pack_start(self.color_button_fg,False, False, 6)
        
        
        """hb.pack_start(Gtk.VSeparator(), False, False, 6)
        hb.pack_start(Gtk.Label(_("Tarajem")), False, False, 0)
        self.tarajem_c = Gtk.ComboBoxText.new()
        self.tarajem_c.set_wrap_width(5)
        if self.__all_tarajem:
            print(self.__all_tarajem)
            for i in self.__all_tarajem.keys():
                self.tarajem_c.append_text(i)
            #self.tarajem_c.set_tooltip_text(_("choose tarajem"))
            #self.tarajem_c.set_active(0)
        else:
            self.tarajem_c.set_sensitive(False)
            self.tarajem_c.set_tooltip_text(_("No Tarajem Available"))
        hb.pack_start(self.tarajem_c, False, False, 0)"""
        
        ############################
        
        self.scale = 1
        self.txt = Gtk.ListStore(str,int,str)
        self.cells = []
        self.cols = []
        self.cells.append(Gtk.CellRendererText())
        #self.cols.append(Gtk.TreeViewColumn('Quranic Text', self.cells[0], markup=0))
        self.cols.append(Gtk.TreeViewColumn('Quranic Text', self.cells[0], text = 0))
        self.cells[0].set_property("background","#fffff8")
        self.cells[0].set_property("foreground","#204000")
        #self.cells[0].set_property("alignment",Pango.ALIGN_CENTER)
        self.cells[0].set_property("wrap-mode", Pango.WrapMode.WORD)
        # TODO: on-max-min also readjust this value
        self.cells[0].set_property("wrap-width", 300)
        self.cells[0].set_property("font", "Amiri 32")
        #self.cells[0].set_property("font", "Simplified Naskh 32")
        #self.cells[0].set_property("font","KFGQPC Uthmanic Script HAFS 32")
        self.cells[0].set_property("scale", self.scale)
        self.cols[0].set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)

        self.cells.append(Gtk.CellRendererText()); # self.cols[-1].set_expand(False)
        self.txt_list = Gtk.TreeView(self.txt)
        self.txt_list.connect("button-press-event",self._on_button_press_event_treeview)
        self.txt_list.set_activate_on_single_click(True)
        self.txt_list.set_hover_selection(Gtk.SelectionMode.NONE   )
        self.txt_list.set_headers_visible(False)
        self.txt_list.set_direction(Gtk.TextDirection.RTL)
        for i in self.cols:
            self.txt_list.insert_column(i, -1)

        self.scroll.add(self.txt_list)
        
        ##################################################################
        last_sura_aya = self.get_last_sura_aya()
        
        
        if last_sura_aya:
            __sura = last_sura_aya[0]
            __aya  = last_sura_aya[1]
            if __sura in (0,8):
                self.sura_c.set_active(__sura)
                self.txt_list.get_selection().select_path((__aya-1,))
                self.txt_list.scroll_to_cell(__aya-1,self.cols[0])
                #self.txt_list.row_activated(Gtk.TreePath.new_from_indices([__aya]),self.cols[0])
            else:
                self.sura_c.set_active(__sura)
                self.txt_list.get_selection().select_path((__aya,))
                self.txt_list.scroll_to_cell(__aya,self.cols[0])
                #self.txt_list.row_activated(Gtk.TreePath.new_from_indices([__aya]),self.cols[0])
        else:
            self.sura_c.set_active(0)
            self.txt_list.get_selection().select_path((last_sura_aya[0],))
            #self.txt_list.row_activated(Gtk.TreePath.new_from_indices([0]),self.cols[0])

        self.menu = Gtk.Menu()
        self.menu.set_screen(Gdk.Screen().get_default())
        
        self.playmenuitem    = Gtk.MenuItem.new_with_label(_("Play"))
        if not self.__all_audio:
            self.playmenuitem.set_sensitive(False)
        self.tarajemmenuitem  = Gtk.MenuItem.new_with_label(_("Tarajem"))
        self.tafasirmenuitem  = Gtk.MenuItem.new_with_label(_("Tafsir"))
        self.copymenuitem     = Gtk.MenuItem.new_with_label(_("Copy"))
        self.colorbgmenuitem  = Gtk.MenuItem.new_with_label(_("bg Color"))
        self.colorfgmenuitem  = Gtk.MenuItem.new_with_label(_("fg  Color"))
    
        self.playmenuitem.connect("activate", self._play_audio,True)
        self.tarajemmenuitem.connect("activate", self.on_tarajem_menu)
        self.tafasirmenuitem.connect("activate", self.on_tafasir_menu)
        self.copymenuitem.connect("activate", self.on_copy_menu)
        self.colorbgmenuitem.connect("activate", self.on_color_menu,self.color_button_bg)
        self.colorfgmenuitem.connect("activate", self.on_color_menu,self.color_button_fg)
        
        self.menu.append(self.playmenuitem)
        self.menu.append(self.tarajemmenuitem)
        self.menu.append(self.tafasirmenuitem)
        self.menu.append(self.copymenuitem)
        self.menu.append(self.colorbgmenuitem)
        self.menu.append(self.colorfgmenuitem)
        self.menu.show_all()
        
        self.build_cp_dlg()
        self.show_all()
        self.zoomOut(None)
        self.connect("key-press-event", self._on_key_press)
        #self.txt_list.connect("row_activated",self.on_row_activated)
        #self.txt_list.connect("cursor_changed",self.on_cursor_changed)

    def on_color_menu(self,button,color_button):
        color_button.emit("clicked")
    
    def _on_add_tilawa_clicked(self,button):
        self._stop_audio()
        w = AddData(self,self.audio_data_location,_("Add Tilawa audio from ayat"))
        w.set_title(_('Add Tilawa from ayat'))
        w.connect("success",self._on_add_tilawa_success)
    
    def _on_add_tilawa_success(self,w=None):
        self.__all_audio = self.get_all_audio_location()   
        if self.__all_audio:
            self.audio_c.remove_all()
            for i in self.__all_audio.keys():
                self.audio_c.append_text(i)
            self.audio_c.set_tooltip_text(_("choose a Audio"))
            self.audio_c.set_active(0)
            self.audio_c.set_sensitive(True)
            self.rewind_b.set_sensitive(True)
            self.forward_b.set_sensitive(True)
            self.play_b.set_sensitive(True)
            self.stop_b.set_sensitive(True)
            self.playmenuitem.set_sensitive(True)

        
    def __on_message(self, bus, message,pipeline1=False):
        t = message.type
        if t == Gst.MessageType.EOS:
            if pipeline1:
                self.tb.set_sensitive(True)
            else:
                aya  = self.get_aya()
                sura = self.get_sura_audio()
                if sura in (1,9) :
                    if aya>=len(self.txt):
                        self.tb.set_sensitive(True)
                        return
                    #self.txt_list.get_selection().select_path((aya,))
                    #self.txt_list.row_activated(Gtk.TreePath.new_from_indices([aya]),self.cols[0])
                    #self.txt_list.scroll_to_cell(aya,self.cols[0])
                else:
                    if aya>=len(self.txt)-1:
                        self.tb.set_sensitive(True)
                        return
                    #self.txt_list.get_selection().select_path((aya+1,))
                    #self.txt_list.row_activated(Gtk.TreePath.new_from_indices([aya]),self.cols[0])
                    #self.txt_list.scroll_to_cell(aya+1,self.cols[0])
                self.resize_cb()
                self.queue_draw()
                self.viewSura(sura)
                self.viewAya(aya+1)
                self._play_audio()
        elif t == Gst.MessageType.ERROR:
            self._stop_audio()
            self.tb.set_sensitive(True)
    

    def seek_audio(self,button=None,forward=True):
        if not self.__can_play:
            return
        if not forward:
            if self.pipeline2.get_state(Gst.CLOCK_TIME_NONE )[1]==Gst.State.PLAYING:
                pos = self.pipeline2.query_position(Gst.Format.TIME)
                if pos :
                    pos = pos[1]
                    if pos>=2*1000000000:
                        self.pipeline2.seek_simple(Gst.Format.TIME,  Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,pos-(2*1000000000))
                    else:
                        self.pipeline2.seek_simple(Gst.Format.TIME,  Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,0)
                        
            elif  self.pipeline.get_state(Gst.CLOCK_TIME_NONE )[1]==Gst.State.PLAYING:
                pos = self.pipeline.query_position(Gst.Format.TIME)
                if pos :
                    pos = pos[1]
                    if pos>=2*1000000000:
                        self.pipeline.seek_simple(Gst.Format.TIME,  Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,pos-(2*1000000000)) 
                    else:
                        self.pipeline2.seek_simple(Gst.Format.TIME,  Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,0)
        else:
            if  self.pipeline2.get_state(Gst.CLOCK_TIME_NONE )[1]==Gst.State.PLAYING:
                pos = self.pipeline2.query_position(Gst.Format.TIME)
                if pos :
                    pos = pos[1]
                    if pos>=0:
                        self.pipeline2.seek_simple(Gst.Format.TIME,  Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,pos+(2*1000000000)) 
            elif  self.pipeline.get_state(Gst.CLOCK_TIME_NONE )[1]==Gst.State.PLAYING:
                pos = self.pipeline.query_position(Gst.Format.TIME)
                if pos :
                    pos = pos[1]
                    if pos>=0:
                        self.pipeline.seek_simple(Gst.Format.TIME,  Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,pos+(2*1000000000))

    def speed_up(self,button=None):
        if self.autoScrolling:
            self.scroll_delay -= 25
            if self.scroll_delay<25:
                self.scroll_delay = 25
            GLib.Source.remove(self.source_id)
            self.source_id = GLib.timeout_add(self.scroll_delay, self.autoScroll, self.tb )
            
    def speed_down(self,button=None):
        if self.autoScrolling:
            self.scroll_delay += 25
            if self.scroll_delay > 500:
                self.scroll_delay = 500
            GLib.Source.remove(self.source_id)
            self.source_id = GLib.timeout_add(self.scroll_delay, self.autoScroll, self.tb )
            

                    
    def _stop_audio(self,button=False):
        self.pipeline2.set_state(Gst.State.NULL)
        self.pipeline.set_state(Gst.State.NULL)
        self.tb.set_sensitive(True)
        
    def _play_audio(self,button=False,oneshot=False):
        if not self.__can_play:
            return
        self._stop_audio()
        self.tb.set_sensitive(False)
        sura = self.get_sura_audio()
        aya  = self.get_aya()
        aya_ = str(aya)
        sura_ = str(sura)
        q = self.__all_audio[self.audio_c.get_active_text()]

        if aya==0 and sura not in (9,1) :
            q = os.path.join(q,"001001.mp3")
        else:
            s_ = ("0"*(3-len(sura_)))+sura_
            a_ = ("0"*(3-len(aya_)))+aya_
            #q = os.path.join(q,sura_.zfill(4-len(sura_))+aya_.zfill(4-len(aya_))+".mp3")
            q = os.path.join(q,s_+a_+".mp3")
        if not os.path.isfile(q):
            self.tb.set_sensitive(True)
            return
        
        if  sys.platform.startswith('win'):
            q =  "file:///"+os.path.abspath(q).replace(os.sep, '/')
        else:
            q = "file://"+os.path.abspath(q)
        if oneshot:
            self.pipeline.set_property('uri',q)
            self.pipeline.set_state(Gst.State.PLAYING)
        else:
            self.pipeline2.set_property('uri',q)
            self.pipeline2.set_state(Gst.State.PLAYING)


    def get_all_audio_location(self):
        result = {}
        if not os.path.isdir(self.audio_data_location):
            return False
        for f in os.listdir(self.audio_data_location):
            ll_ = os.path.join(self.audio_data_location,f)
            for dirname,folder,files in os.walk(ll_):
                for file_ in files:
                    if file_.endswith(".mp3"):
                        result.setdefault(os.path.basename(dirname),dirname)
                        break
        if result:
            return result
        return False

        
    def on_tarajem_menu(self,w):
        self.get_current_info_aya_tarajem()
        
    def on_tafasir_menu(self,w):
        self.get_current_info_aya_tafasir()
         
    def on_copy_menu(self,w):
        a = self.txt_list.get_selection().get_selected()
        if a:
            aya = self.txt[self.txt.get_path(a[1])][0]
            self.clip2.set_text(aya, -1) 
        
        
    def _on_button_press_event_treeview(self,treeview,event):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            self.menu.popup_at_pointer()
            self.queue_draw()
            #while Gtk.events_pending():
            #    Gtk.main_iteration()
            #self.menu.show_all()
            
    def _on_key_press(self,widget, event):
        if (event.state & Gdk.ModifierType.CONTROL_MASK) and event.keyval == Gdk.KEY_s:
            self.save_sura_aya()
            
        elif  (event.state & Gdk.ModifierType.CONTROL_MASK) and event.keyval == Gdk.KEY_d:
            self.darkmode_switch.set_active(not self.darkmode_switch.get_active())
            
        elif  (event.state & Gdk.ModifierType.CONTROL_MASK) and event.keyval == Gdk.KEY_f:
            self.search.grab_focus_without_selecting()
                
        elif  (event.state & Gdk.ModifierType.CONTROL_MASK) and event.keyval == Gdk.KEY_z:
            self.zoomIn()
            
        elif  (event.state & Gdk.ModifierType.CONTROL_MASK) and event.keyval == Gdk.KEY_x:
            self.zoomOut()
            
        elif  (event.state & Gdk.ModifierType.CONTROL_MASK) and event.keyval == Gdk.KEY_a:
            self.menu.popup_at_pointer()
            self.menu.show_all()
            
        elif  (event.state & Gdk.ModifierType.CONTROL_MASK) and event.keyval == Gdk.KEY_e:
            #self.sura_c.grab_focus()
            self.sura_c.popup()
                        
        elif  (event.state & Gdk.ModifierType.CONTROL_MASK) and event.keyval == Gdk.KEY_c :
            if  self.pipeline2.get_state(Gst.CLOCK_TIME_NONE )[1]!=Gst.State.PLAYING:
                self.autoScrolling = not self.autoScrolling
                self.tb.set_active(not self.tb.get_active() )

            
        elif  (event.state & Gdk.ModifierType.CONTROL_MASK) and event.keyval == Gdk.KEY_b and self.autoScrolling:
            self.speed_up()
            
        elif  (event.state & Gdk.ModifierType.CONTROL_MASK) and event.keyval == Gdk.KEY_v and self.autoScrolling:
            self.speed_down()

        elif  (event.state & Gdk.ModifierType.CONTROL_MASK) and event.keyval == Gdk.KEY_q :
            self.cp_b.emit("clicked")
        
        elif  (event.state & Gdk.ModifierType.CONTROL_MASK) and event.keyval == Gdk.KEY_g :
            if self.audio_c.get_sensitive():
                if  self.pipeline2.get_state(Gst.CLOCK_TIME_NONE )[1]!=Gst.State.PLAYING:
                    self._play_audio(None)
                
        elif  (event.state & Gdk.ModifierType.CONTROL_MASK) and event.keyval == Gdk.KEY_h :
            if self.audio_c.get_sensitive():
                self._stop_audio()
                
        elif  (event.state & Gdk.ModifierType.CONTROL_MASK) and event.keyval == Gdk.KEY_Left  :
            if self.audio_c.get_sensitive() and self.pipeline2.get_state(Gst.CLOCK_TIME_NONE )[1]==Gst.State.PLAYING:
                self.seek_audio(None,False)  
                
        elif  (event.state & Gdk.ModifierType.CONTROL_MASK) and event.keyval == Gdk.KEY_Right  :
            if self.audio_c.get_sensitive() and self.pipeline2.get_state(Gst.CLOCK_TIME_NONE )[1]==Gst.State.PLAYING:
                self.seek_audio() 
                

            
        """elif  (event.state & Gdk.ModifierType.SHIFT_MASK) and (event.state & Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK):
            print("dddddddddd)"""
        self.queue_draw()
        
    def save_last_sura_aya(self,sura,aya):
        config_location = os.path.join(GLib.get_user_config_dir(),"othman")
        config_file     = os.path.join(config_location,"othman.json")
        try:
            os.makedirs(config_location,exist_ok=True)
            with open(config_file,"w") as mf:
                json.dump({"sura":sura,"aya":aya},mf,indent=4)
        except Exception as e:
            print(e)
            return False
        return True

    def get_last_sura_aya(self):
        config_file = os.path.join(os.path.join(GLib.get_user_config_dir(),"othman"),"othman.json")
        if os.path.isfile(config_file):
            try:
                with open(config_file) as mf:
                    config = json.load(mf)
            except Exception as e:
                print(e)
                return False
            return config["sura"],config["aya"]
        return False
    
    def get_sura_aya(self):
        return self.sura_c.get_active(),self.get_aya()
        
    def get_aya(self):
        treemodel_treeiter = self.txt_list.get_selection().get_selected()
        if not treemodel_treeiter:
            aya = 0
        else:
            aya = treemodel_treeiter[0].get_value(treemodel_treeiter[1],1)
        return aya
        
    def get_sura_audio(self):
        return self.sura_c.get_active()+1

    def save_sura_aya(self):
        self.save_last_sura_aya(self.sura_c.get_active(),self.get_aya())
        
    #def on_cursor_changed(self,tree_view):
     #   print(tree_view)

    """def on_row_activated(self,tree_view, path, column):
        treemodel_treeiter = self.txt_list.get_selection().get_selected()
        if not treemodel_treeiter:
            self.__aya = 0
        else:
            self.__aya = treemodel_treeiter[0].get_value(treemodel_treeiter[1],1)
        print(self.__aya)
        soura = self.sura_c.get_active()+1
        aya   = path
        a = tree_view.get_cell_area(aya, column)
        #self.cells[0].get_style_context().add_class("glow")
        for row in self.txt:
            print(self.txt[row.iter][0])
            print(self.txt[row.iter][1])
            print(self.txt[row.iter][2])
        self.txt_list.get_selection().select_path((10,))
        self.txt_list.scroll_to_cell(10,column)"""

        
        
    ############################
    def _on_color_set(self,colorbutton,bg=True):
        if bg:
            self.cells[0].set_property("background",colorbutton.get_color().to_string())
        else:
            self.cells[0].set_property("foreground",colorbutton.get_color().to_string())
        
    def _on_darkmode_switch_state_changed(self,switch,state,defaultsettings):
        defaultsettings.props.gtk_application_prefer_dark_theme  = state
        if state:
            self.color_button_bg.set_color(Gdk.Color.parse("#323030")[-1])
            self.color_button_fg.set_color(Gdk.Color.parse("#fffff8")[-1])
            self.cells[0].set_property("background","#323030")
            self.cells[0].set_property("foreground","#fffff8")
        else:
            self.color_button_bg.set_color(Gdk.Color.parse("#fffff8")[-1])
            self.color_button_fg.set_color(Gdk.Color.parse("#204000")[-1])
            self.cells[0].set_property("background","#fffff8")
            self.cells[0].set_property("foreground","#204000")
    ############################
    
    def show_about_dlg(self, parent):
        dlg = Gtk.AboutDialog()
        dlg.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        dlg.set_modal(True)
        dlg.set_transient_for(parent)
        dlg.set_default_response(Gtk.ResponseType.CLOSE)
        dlg.connect('delete-event', lambda w,*a: w.hide() or True)
        dlg.connect('response', lambda w,*a: w.hide() or True)
        try:
            dlg.set_program_name("Othman")
        except:
            pass
        dlg.set_name(_('Othman Quran Browser'))
        #dlg.set_version(version)
        dlg.set_copyright("Copyright © 2008-2010 Muayyad Saleh Alsadi <alsadi@ojuba.org>")
        dlg.set_comments(_("Electronic Mus-haf"))
        dlg.set_license("""
        Released under terms of Waqf Public License.
        This program is free software; you can redistribute it and/or modify
        it under the terms of the latest version Waqf Public License as
        published by Ojuba.org.

        This program is distributed in the hope that it will be useful,
        but WITHOUT ANY WARRANTY; without even the implied warranty of
        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

        The Latest version of the license can be found on
        "http://waqf.ojuba.org/"

        """)
        dlg.set_website("http://othman.ojuba.org/")
        dlg.set_website_label("http://othman.ojuba.org")
        dlg.set_authors(["Muayyad Saleh Alsadi <alsadi@ojuba.org>"])
        dlg.set_translator_credits(_("translator-credits"))
        fn = os.path.join(self.data_dir, "quran-kareem.svg")
        try:
            logo = GdkPixbuf.Pixbuf.new_from_file_at_size(fn, 128, 128)
        except:
            fn = os.path.join(self.data_dir, "quran-kareem.png")
            logo = GdkPixbuf.pixbuf_new_from_file(fn)
        dlg.set_logo(logo)
        #dlg.set_logo_icon_name('Othman')
        dlg.run()
        dlg.destroy()

    def search_cb(self, b, *a):
        if not self.sw:
            self.sw = searchWindow(self)
        self.sw.find(b.get_text())

    def autoScroll(self, b):
        if not self.autoScrolling:
            self.__can_play = True
            self.scroll_delay = 200
            return True
        v = self.scroll.get_vadjustment()
        m = v.get_upper() - v.get_page_size()
        n = min(m, v.get_value() + 2 )
        if n == m:
            self.scroll_delay = 200
            b.set_active(False)
            self.__can_play = True
        v.set_value(n)
        """if b.get_active() :
            if self.__count>(self.scroll_delay+self.cells[0].get_property("scale")):
                sura,aya = self.get_sura_aya()
                self.txt_list.get_selection().select_path((aya+1,))
                self.__count = 0
            self.__count +=5"""
        return True

    def autoScrollCb(self, b, *a):
        isactive           = b.get_active()
        self.__can_play    = not isactive
        self.autoScrolling = isactive

    def zoomIn(self, *a):
        sura, aya = self.getCurrentSuraAya()
        self.scale += 0.1
        self.cells[0].set_property("scale", self.scale)
        self.resize_cb()
        self.queue_draw()
        self.viewSura(sura)
        self.viewAya(aya)

    def zoomOut(self, *a):
        sura, aya = self.getCurrentSuraAya()
        self.scale -= 0.1
        self.scale = max(0.2, self.scale)
        self.cells[0].set_property("scale", self.scale)
        self.resize_cb()
        self.queue_draw()
        self.viewSura(sura)
        self.viewAya(aya)

    def viewAya(self, aya, sura = None):
        if sura == None:
            sura = self.sura_c.get_active() + 1
        aya = max(1,abs(aya))
        i = aya + int(self.showSunnahBasmala(sura))
        self.txt_list.scroll_to_cell((i - 1,))
        self.txt_list.get_selection().select_path((i - 1,))
        

    def viewSura(self, i):
        #self.play_pause.set_active(False)
        self.txt.clear()
        if self.showSunnahBasmala(i):
            #self.txt.append(['<span foreground="#440000">%s</span>' % self.basmala,0,])
            self.txt.append([self.basmala, 0, "#802000",])
        for j, k in enumerate(self.getSuraIter(i)):
            self.txt.append([k[0], j + 1, "#204000",])
        self.resize_cb()
        self.scroll.get_vadjustment().set_value(0)
        self.txt_list.get_selection().select_path((0,))


    def sura_changed_cb(self, c, *a):
        self.viewSura(self.sura_c.get_active() + 1)
        self._stop_audio()
        self.tb.set_active(False)

    def resize_cb(self,*args):
        if self.cols[0].get_width() > 10:
            self.cells[0].set_property("wrap-width", self.cols[0].get_width() - 10)

    def cp_cb(self, *a):
        sura = self.cp_sura.get_active() + 1
        aya1 = self.cp_from.get_value()
        aya2 = self.cp_to.get_value()
        n = aya2 - aya1 + 1
        i = self.cp_is_imlai.get_active()
        a = [' ', '\n', ' * ', ' *\n']
        s = a[int(i) * 2 + int(self.cp_aya_perline.get_active())]
        s = s.join([l[i] for l in self.getSuraIter(sura, n, aya1)]) + '\n'
        self.clip1.set_text(s, -1)
        self.clip2.set_text(s, -1)
        self.cp_w.hide()

    def cp_sura_cb(self, *a):
        sura = self.cp_sura.get_active() + 1
        m = self.suraInfoById[sura - 1][5]
        self.cp_from.set_range(1, m)
        self.cp_to.set_range(1, m)
        self.cp_from.set_value(1)
        self.cp_to.set_value(m)

    def show_cp_dlg(self, *a):
        sura, aya = self.getCurrentSuraAya()
        aya = max(1, abs(aya))
        self.cp_sura.set_active(sura - 1)
        self.cp_sura_cb()
        self.cp_from.set_value(aya)
        self.cp_w.show_all()

    def build_cp_dlg(self):
        self.cp_w = Gtk.Window()
        self.cp_w.set_position(Gtk.WindowPosition.CENTER )
        self.cp_w.set_title(_('Copy to clipboard'))
        self.cp_w.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.cp_w.connect('delete-event', lambda w,*a: w.hide() or True)
        self.cp_sura = Gtk.ComboBoxText.new()
        self.cp_sura.set_wrap_width(5)

        for i in self.sura_ls:
            self.cp_sura.append_text(i)
        self.cp_sura.set_tooltip_text(_("choose a Sura"))
        adj = Gtk.Adjustment(0, 0, 286, 1, 10, 0)
        self.cp_from = s = Gtk.SpinButton()
        s.set_adjustment(adj)
        adj = Gtk.Adjustment(0, 0, 286, 1, 10, 0)
        self.cp_to = s = Gtk.SpinButton()
        s.set_adjustment(adj)
        self.cp_is_imlai = Gtk.CheckButton(_("Imla'i style"))
        self.cp_aya_perline = Gtk.CheckButton(_("an Aya per line"))
        self.cp_ok = Gtk.Button(stock=Gtk.STOCK_OK)
        self.cp_cancel = Gtk.Button(stock=Gtk.STOCK_CANCEL)
        vb = Gtk.VBox(False,0)
        self.cp_w.add(vb)
        hb = Gtk.HBox(False,3)
        vb.pack_start(hb,True,True,3)
        hb.pack_start(Gtk.Label(_("Sorat:")),False,False,3)
        hb.pack_start(self.cp_sura,False,False,6)
        hb = Gtk.HBox(False,6)
        vb.pack_start(hb,True,True,6)
        hb.pack_start(Gtk.Label(_("Ayat from:")),False,False,3)
        hb.pack_start(self.cp_from,False,False,3)
        hb.pack_start(Gtk.Label(_("To")),False,False,3)
        hb.pack_start(self.cp_to,False,False,3)
        hb = Gtk.HBox(False,6)
        vb.pack_start(hb,True,True,6)
        hb.pack_start(self.cp_is_imlai,False,False,3)
        hb.pack_start(self.cp_aya_perline,False,False,3)
        hb = Gtk.HBox(False,6)
        vb.pack_start(hb,True,True,6)
        hb.pack_start(self.cp_ok,False,False,6)
        hb.pack_start(self.cp_cancel,False,False,6)
        self.cp_sura.connect("changed", self.cp_sura_cb)
        self.cp_cancel.connect('clicked', lambda *args: self.cp_w.hide())
        self.cp_ok.connect('clicked', self.cp_cb)
        self.cp_is_imlai.set_active(True)

    def getCurrentSuraAya(self):
        a = self.txt_list.get_selection().get_selected()
        aya = 1
        if a:
            aya = self.txt[self.txt.get_path(a[1])][1]
        aya = max(aya, 1)
        return self.sura_c.get_active() + 1, aya

    def get_current_info_aya_tarajem(self):
        sura_n,aya_n = self.get_sura_aya()
        conn = None
        sura = self.sura_c.get_active_text()
        a = self.txt_list.get_selection().get_selected()
        aya = self.txt[self.txt.get_path(a[1])][0]
        self._stop_audio()
        ShowTarajemTafasir(self,self.tarajem_data_location ,
                    _("Add Tarajem Sources"),
                    _("Add Tarajem from ayat"),_("Show Tarajem"),sura_n+1,aya_n,sura,aya,_("Tarajem Not Available"),self.__all_audio,True)

    def get_current_info_aya_tafasir(self):
        sura_n,aya_n = self.get_sura_aya()
        conn = None
        sura = self.sura_c.get_active_text()
        a = self.txt_list.get_selection().get_selected()
        aya = self.txt[self.txt.get_path(a[1])][0]
        self._stop_audio()
        ShowTarajemTafasir(self,self.tafasir_data_location ,
                    _("Add Tafasir Sources"),
                    _("Add Tafasir from ayat"),_("Show Tafasir"),sura_n+1,aya_n,sura,aya,_("Tafasir Not Available"),self.__all_audio,False)

    def quit(self,*args):
        last_sura_aya_config  = self.get_last_sura_aya()
        last_sura_aya_current = self.get_sura_aya()
        if last_sura_aya_config:
            if last_sura_aya_config!=last_sura_aya_current:
                y_o_n = Yes_Or_No(_("Save Current Sura/Aya?"),self,"")
                if y_o_n.check():
                    self.save_sura_aya()
        else:
            self.save_sura_aya()
        Gtk.main_quit()
        return True


"""def set_language(domain,ld):
    languages = []
    for lang in [i for i in os.listdir(ld) if os.path.isdir(os.path.join(ld,i))]:
        if gettext.find(domain, localedir=ld, languages=[lang]):
            languages.append(lang)
    if languages:
        l = gettext.translation(domain, localedir=ld, languages=languages)
        l.install()
        return True
    return False"""
    
def main():
    if sys.platform.startswith('win'):
        import locale
        if os.getenv('LANG') is None:
            lang, enc = locale.getdefaultlocale()
            os.environ['LANG'] = lang
    is_pyinstaller = getattr(sys, 'frozen',False) and hasattr(sys, '_MEIPASS')
    if   is_pyinstaller:
        ld = get_correct_path('locale')
        othman_data = os.path.join(GLib.get_user_data_dir(),"othman")
    else:
        exedir = os.path.dirname(sys.argv[0])
        ld = os.path.join(exedir,'..', 'share', 'locale')
        if not os.path.exists(ld):
            ld = os.path.join(exedir, 'locale')
        othman_data = os.path.abspath(os.path.join(exedir,"othman-data"))
        if  not os.path.isdir(othman_data):
            othman_data = os.path.join(GLib.get_user_data_dir(),"othman")
            os.makedirs(othman_data,exist_ok=True)
    gettext.install('othman', localedir=ld)
    w = othmanUi(othman_data)
    Gtk.main()

if __name__ == "__main__":
    main()

