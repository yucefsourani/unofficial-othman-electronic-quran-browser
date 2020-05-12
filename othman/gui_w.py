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
            self.parent.emit("success")
            
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
                
class AddTilawa(Gtk.Window):
    __gsignals__ = {
        "success"     : (GObject.SignalFlags.RUN_LAST, None, ()),
    }
    
    def __init__(self, w=None,audio_data_location=""):
        Gtk.Window.__init__(self)
        self.w = w
        self.audio_data_location = audio_data_location
        self.set_size_request(600, 400)
        self.__files = []
        
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
        self.set_title(_('Add Tilawa from ayat'))
        self.set_transient_for(w)
        vb = Gtk.VBox()
        hb = Gtk.HBox()
        
        linkbutton = Gtk.LinkButton.new_with_label("http://quran.ksu.edu.sa/ayat/?l=ar&pg=patches","http://quran.ksu.edu.sa")
        
        label      = Gtk.Label()
        label.get_style_context().add_class("h2")
        label.set_label(_("Add Tilawa audio from ayat"))
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
        self.open_audio_location_button.props.label = _("Open Audio Location")
        self.open_audio_location_button.connect("clicked",self.on_open_audio_location_button_clicked)
        
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
        
    def on_open_audio_location_button_clicked(self,button):
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
        Gtk.MessageDialog.__init__(self,buttons = Gtk.ButtonsType.OK_CANCEL)
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
