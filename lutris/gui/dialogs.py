# -*- coding: utf-8 -*-
"""Common message dialogs"""
import os
from gi.repository import Gtk, GObject

from lutris.gui.widgets import DownloadProgressBox

from lutris import settings
from lutris import pga
from lutris import api


class GtkBuilderDialog(GObject.Object):

    def __init__(self):
        super(GtkBuilderDialog, self).__init__()
        ui_filename = os.path.join(settings.get_data_path(), 'ui',
                                   self.glade_file)
        if not os.path.exists(ui_filename):
            ui_filename = None

        self.builder = Gtk.Builder()
        self.builder.add_from_file(ui_filename)
        self.dialog = self.builder.get_object(self.dialog_object)
        self.builder.connect_signals(self)
        self.dialog.show_all()

    def on_close(self, *args):
        self.dialog.destroy()


class AboutDialog(GtkBuilderDialog):
    glade_file = 'AboutDialog.ui'
    dialog_object = "about_dialog"


class NoticeDialog(Gtk.MessageDialog):
    """ Displays a message to the user. """
    def __init__(self, message):
        super(NoticeDialog, self).__init__(buttons=Gtk.ButtonsType.OK)
        from lutris import api
        self.set_markup(message)
        self.run()
        self.destroy()


class ErrorDialog(Gtk.MessageDialog):
    """ Displays an error message. """
    def __init__(self, message):
        super(ErrorDialog, self).__init__(buttons=Gtk.ButtonsType.OK)
        self.set_markup(message)
        self.run()
        self.destroy()


class QuestionDialog(Gtk.MessageDialog):
    """ Asks a question. """
    def __init__(self, settings):
        super(QuestionDialog, self).__init__(
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            message_format=settings['question']
        )
        self.set_title(settings['title'])
        self.result = self.run()
        self.destroy()


class DirectoryDialog(Gtk.FileChooserDialog):
    """Ask the user to select a directory"""
    def __init__(self, message):
        super(DirectoryDialog, self).__init__(
            title=message,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
            buttons=(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE,
                     Gtk.STOCK_OK, Gtk.ResponseType.OK)
        )
        self.result = self.run()
        self.folder = self.get_current_folder()
        self.destroy()


class FileDialog(Gtk.FileChooserDialog):
    def __init__(self):
        super(FileDialog, self).__init__(
            "Please choose a file", None, Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        )
        response = self.run()
        if response == Gtk.ResponseType.OK:
            self.filename = self.get_filename()
        elif response == Gtk.ResponseType.CANCEL:
            self.filename = False
        self.destroy()


class DownloadDialog(Gtk.Dialog):
    """ Dialog showing a download in progress. """

    def __init__(self, url, dest):
        super(DownloadDialog, self).__init__("Downloading file")
        self.set_size_request(560, 100)
        params = {'url': url, 'dest': dest}
        self.download_progress_box = DownloadProgressBox(params)
        self.download_progress_box.connect('complete',
                                           self.download_complete)
        self.download_progress_box.connect('cancelrequested',
                                           self.download_cancelled)
        label = Gtk.Label(label='Downloading %s' % url)
        label.set_selectable(True)
        label.set_padding(0, 0)
        label.set_alignment(0.0, 1.0)
        self.vbox.pack_start(label, True, True, 0)
        self.vbox.pack_start(self.download_progress_box, True, False, 0)
        self.show_all()
        self.download_progress_box.start()

    def download_complete(self, _widget, _data):
        self.destroy()

    def download_cancelled(self, _widget, data):
        self.destroy()


class PgaSourceDialog(GtkBuilderDialog):
    glade_file = 'dialog-pga-sources.ui'
    dialog_object = 'pga_dialog'

    def __init__(self):
        super(PgaSourceDialog, self).__init__()

        # GtkBuilder Objects
        self.sources_selection = self.builder.get_object("sources_selection")
        self.sources_treeview = self.builder.get_object("sources_treeview")
        self.remove_source_button = self.builder.get_object(
            "remove_source_button"
        )

        # Treeview setup
        self.sources_liststore = Gtk.ListStore(str)
        renderer = Gtk.CellRendererText()
        renderer.set_padding(4, 10)
        uri_column = Gtk.TreeViewColumn("URI", renderer, text=0)
        self.sources_treeview.append_column(uri_column)
        self.sources_treeview.set_model(self.sources_liststore)
        sources = pga.read_sources()
        for index, source in enumerate(sources):
            self.sources_liststore.append((source, ))

        self.remove_source_button.set_sensitive(False)
        self.dialog.show_all()

    @property
    def sources_list(self):
        return [source[0] for source in self.sources_liststore]

    def on_apply(self, widget, data=None):
        pga.write_sources(self.sources_list)
        self.on_close(widget, data)

    def on_add_source_button_clicked(self, widget, data=None):
        chooser = Gtk.FileChooserDialog(
            "Select directory", self.dialog,
            Gtk.FileChooserAction.SELECT_FOLDER,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            "Select", Gtk.ResponseType.OK)
        )
        chooser.set_local_only(False)
        response = chooser.run()
        if response == Gtk.ResponseType.OK:
            uri = chooser.get_uri()
            if uri not in self.sources_list:
                self.sources_liststore.append((uri, ))
        chooser.destroy()

    def on_remove_source_button_clicked(self, widget, data=None):
        """ Remove a source """
        (model, treeiter) = self.sources_selection.get_selected()
        if treeiter:
            # TODO : Add confirmation
            model.remove(treeiter)

    def on_sources_selection_changed(self, widget, data=None):
        """ Set sentivity of remove source button """
        (model, treeiter) = self.sources_selection.get_selected()
        self.remove_source_button.set_sensitive(treeiter is not None)


class ClientLoginDialog(GtkBuilderDialog):
    glade_file = 'dialog-lutris-login.ui'
    dialog_object = 'lutris-login'
    __gsignals__ = {
        "connected": (GObject.SIGNAL_RUN_FIRST, None, (str, )),
    }

    def __init__(self):
        super(ClientLoginDialog, self).__init__()

        cancel_button = self.builder.get_object('cancel_button')
        cancel_button.connect('clicked', self.on_cancel)
        connect_button = self.builder.get_object('connect_button')
        connect_button.connect('clicked', self.on_connect)

    def on_cancel(self, widget):
        self.dialog.destroy()

    def on_connect(self, widget):
        username = self.builder.get_object('username_entry').get_text()
        password = self.builder.get_object('password_entry').get_text()
        token = api.connect(username, password)
        if not token:
            NoticeDialog("Login failed")
        else:
            self.emit('connected', token)
        self.dialog.destroy()