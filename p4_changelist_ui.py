import os, mimetypes, filecmp
from tkinter import *
from tkinter.filedialog import askopenfilename, askdirectory
import zipfile

from difflibparser.difflibparser import *
from python_difflib_gui.ui.mainwindow_ui import MainWindowUI
from p4_changelist_patch import apply_to_content


class P4CLMainWindow:
    def start(self, changeListFile = None):
        self.main_window = Tk()
        self.main_window.title('P4 ChangeList Viewer')
        self.__main_window_ui = MainWindowUI(self.main_window)

        self.leftFile = StringVar()
        self.rightFile = StringVar()
        self.leftFile.trace('w', lambda *x:self.__filesChanged())
        self.rightFile.trace('w', lambda *x:self.__filesChanged())

        self.__main_window_ui.center_window()
        self.__main_window_ui.create_file_path_labels()
        self.__main_window_ui.create_text_areas()
        self.__main_window_ui.create_line_numbers()
        self.__main_window_ui.create_scroll_bars()
        self.__main_window_ui.create_file_treeview()
        path_to_my_project = os.getcwd()
        self.__main_window_ui.add_menu('File', [
            {'name': 'Open ChangeList Dump', 'command': self.__browse_files},
            {'separator'},
            {'name': 'Exit', 'command': self.exit}
            ])
        self.__main_window_ui.fileTreeView.column("#0", stretch=False, width=250, minwidth=150)
        self.__main_window_ui.fileTreeView.bind('<<TreeviewSelect>>', lambda *x:self.__treeViewItemSelected())

        self.main_window.bind('<Key>', self.__key_event)

        self.changeListFile = None
        self.cur_diff_index = 0
        self.diff_index = []

        if changeListFile:
            self.__load_changelist_file(changeListFile)

        self.main_window.mainloop()

    # Callback for changing a file path
    def __filesChanged(self):
        self.__main_window_ui.leftLinenumbers.grid_remove()
        self.__main_window_ui.rightLinenumbers.grid_remove()
        if self.leftFile.get() == None or self.rightFile.get() == None:
            self.__main_window_ui.leftFileTextArea.config(background=self.__main_window_ui.grayColor)
            self.__main_window_ui.rightFileTextArea.config(background=self.__main_window_ui.grayColor)
            return

        self.__main_window_ui.leftFileLabel.config(text=self.leftFile.get())
        self.__main_window_ui.rightFileLabel.config(text=self.rightFile.get())
        self.__main_window_ui.leftFileTextArea.config(background=self.__main_window_ui.whiteColor)
        self.__main_window_ui.rightFileTextArea.config(background=self.__main_window_ui.whiteColor)
        self.__main_window_ui.leftLinenumbers.grid()
        self.__main_window_ui.rightLinenumbers.grid()
        self.__diff_files_into_text_areas()

    def __treeViewItemSelected(self):
        item_id = self.__main_window_ui.fileTreeView.focus()
        paths = self.__main_window_ui.fileTreeView.item(item_id)['values']
        if paths == None or len(paths) == 0:
            return
        self.leftFile.set(paths[0])
        self.rightFile.set(paths[0] + ".patch")

    # Insert file contents into text areas and highlight differences
    def __diff_files_into_text_areas(self):
        if self.rightFile.get() == '' or self.leftFile.get() == '':
            return

        leftFileContents = self.__load_changelist_data(self.leftFile.get())
        rightFileContents = self.__load_changelist_data(self.rightFile.get())

        rightFileContents, code = apply_to_content(leftFileContents, rightFileContents)

        if not rightFileContents or code != 0:
            self.__main_window_ui.leftFileTextArea.config(background=self.__main_window_ui.grayColor)
            self.__main_window_ui.rightFileTextArea.config(background=self.__main_window_ui.grayColor)
            return

        diff = DifflibParser(leftFileContents.decode('utf-8', errors='ignore').splitlines(),
                             rightFileContents.decode('utf-8', errors='ignore').splitlines())

        # enable text area edits so we can clear and insert into them
        self.__main_window_ui.leftFileTextArea.config(state=NORMAL)
        self.__main_window_ui.rightFileTextArea.config(state=NORMAL)
        self.__main_window_ui.leftLinenumbers.config(state=NORMAL)
        self.__main_window_ui.rightLinenumbers.config(state=NORMAL)

        # clear all text areas
        self.__main_window_ui.leftFileTextArea.delete(1.0, END)
        self.__main_window_ui.rightFileTextArea.delete(1.0, END)
        self.__main_window_ui.leftLinenumbers.delete(1.0, END)
        self.__main_window_ui.rightLinenumbers.delete(1.0, END)

        lineno = 1
        record_lineno = 0

        def save_index(lineno, record_lineno):
            if record_lineno == 0 or lineno != record_lineno + 1:
                self.diff_index.append('{}.0'.format(lineno))
            record_lineno = lineno

            return record_lineno

        for line in diff:
            if line['code'] == DiffCode.SIMILAR:
                self.__main_window_ui.leftFileTextArea.insert('end', line['line'] + '\n')
                self.__main_window_ui.rightFileTextArea.insert('end', line['line'] + '\n')
            elif line['code'] == DiffCode.RIGHTONLY:
                self.__main_window_ui.leftFileTextArea.insert('end', '\n', 'gray')
                self.__main_window_ui.rightFileTextArea.insert('end', line['line'] + '\n', 'green')

                record_lineno = save_index(lineno, record_lineno)
            elif line['code'] == DiffCode.LEFTONLY:
                self.__main_window_ui.leftFileTextArea.insert('end', line['line'] + '\n', 'red')
                self.__main_window_ui.rightFileTextArea.insert('end', '\n', 'gray')

                record_lineno = save_index(lineno, record_lineno)
            elif line['code'] == DiffCode.CHANGED:
                record_lineno = save_index(lineno, record_lineno)

                for (i,c) in enumerate(line['line']):
                    self.__main_window_ui.leftFileTextArea.insert('end', c, 'darkred' if i in line['leftchanges'] else 'red')
                for (i,c) in enumerate(line['newline']):
                    self.__main_window_ui.rightFileTextArea.insert('end', c, 'darkgreen' if i in line['rightchanges'] else 'green')
                self.__main_window_ui.leftFileTextArea.insert('end', '\n')
                self.__main_window_ui.rightFileTextArea.insert('end', '\n')
            self.__main_window_ui.leftLinenumbers.insert('end', str(lineno) + '\n', 'line')
            self.__main_window_ui.rightLinenumbers.insert('end', str(lineno) + '\n', 'line')
            lineno += 1

        # calc width of line numbers texts and set it
        width = len(str(lineno))
        self.__main_window_ui.leftLinenumbers.config(width=width)
        self.__main_window_ui.rightLinenumbers.config(width=width)

        # disable text areas to prevent further editing
        self.__main_window_ui.leftFileTextArea.config(state=DISABLED)
        self.__main_window_ui.rightFileTextArea.config(state=DISABLED)
        self.__main_window_ui.leftLinenumbers.config(state=DISABLED)
        self.__main_window_ui.rightLinenumbers.config(state=DISABLED)
        self.__main_window_ui.leftFileTextArea.focus_set()

        self.__goto_cur_diff()

    def __browse_files(self):
        fname = askopenfilename()

        if fname:
            self.__load_changelist_file(fname)
        else:
            self.__main_window_ui.fileTreeView.grid_remove()
            self.__main_window_ui.fileTreeYScrollbar.grid_remove()
            self.__main_window_ui.fileTreeXScrollbar.grid_remove()

    def exit(self):
        self.main_window.destroy()

    def __load_changelist_file(self, changeListFile):
        dirs_cache = {}

        self.changeListFile = changeListFile
        self.leftFile.set('')
        self.rightFile.set('')
        self.cur_diff_index = 0
        self.diff_index = []

        self.__main_window_ui.fileTreeView.grid()
        self.__main_window_ui.fileTreeYScrollbar.grid()
        self.__main_window_ui.fileTreeXScrollbar.grid()
        self.__main_window_ui.fileTreeView.delete(*self.__main_window_ui.fileTreeView.get_children())

        with zipfile.ZipFile(changeListFile) as z_archive:
            for z_info in z_archive.infolist():
                if z_info.is_dir() or z_info.filename.endswith('.patch'):
                    continue

                dirs, f_name = os.path.split(z_info.filename)

                parent = self.__create_parent_dirs(dirs_cache, dirs)

                self.__main_window_ui.fileTreeView.insert(parent,
                                                          'end',
                                                          text=f_name,
                                                          open=False,
                                                          value=(z_info.filename),
                                                          tags=('black', 'simple'))

    def __create_parent_dirs(self, dirs_cache, dirs):
        if dirs in dirs_cache:
            return dirs_cache[dirs]

        if dirs == '/' or not dirs:
            return ''

        parent_dirs, cur_dir = os.path.split(dirs)

        parent = self.__create_parent_dirs(dirs_cache, parent_dirs)

        oid = self.__main_window_ui.fileTreeView.insert(parent, 'end', text=cur_dir, open=False)

        dirs_cache[dirs] = oid

        return oid

    def __load_changelist_data(self, file_name):
        with zipfile.ZipFile(self.changeListFile) as z_archive:
            with z_archive.open(file_name, 'r') as z_file:
                return z_file.read()

    def __key_event(self, event):
        if len(self.diff_index) == 0:
            return

        if event.keysym == 'Down':
            if self.cur_diff_index < len(self.diff_index) - 1:
                self.cur_diff_index += 1
            self.__goto_cur_diff()
        if event.keysym == 'Up':
            if self.cur_diff_index > 0:
                self.cur_diff_index -= 1
            self.__goto_cur_diff()

    def __goto_cur_diff(self):
        if self.cur_diff_index < len(self.diff_index):
            self.__main_window_ui.leftFileTextArea.see(self.diff_index[self.cur_diff_index])
