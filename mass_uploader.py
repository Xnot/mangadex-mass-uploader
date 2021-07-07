import tkinter as tk
from tkinter import filedialog
from tkinter import ttk

import pandas as pd

from mangadex_api import MangaDexAPI


class MassUploader(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MangaDex Mass Uploader")
        self.mangadex = MangaDexAPI()
        self.frame = ttk.Frame(self, padding=5)
        self.frame.grid(row=0, column=0)
        log_frame = ttk.Frame(self, padding=5)
        log_frame.grid(row=0, column=1)
        self.log = tk.Text(log_frame, bg="black", fg="white", width=40)
        self.log.pack()
        self.print_log("hello")
        self.render_login()

    def render_login(self):
        username = tk.StringVar(self.frame)
        password = tk.StringVar(self.frame)
        login_call = lambda event=None: self.login(username.get(), password.get())

        ttk.Label(self.frame, text="Username").grid(row=0, column=0)
        ttk.Entry(self.frame, textvariable=username).grid(row=0, column=1)
        ttk.Label(self.frame, text="Password").grid(row=1, column=0)
        ttk.Entry(self.frame, textvariable=password, show="☺").grid(row=1, column=1)
        ttk.Button(self.frame,
                   text="Login",
                   default="active",
                   command=login_call).grid(row=3, column=1)
        self.bind('<Return>', login_call)
        self.pad_children()

    def login(self, username, password):
        try:
            self.mangadex.login(username, password)
        except Exception as e:
            self.print_log(e)
        else:
            self.print_log("logged in successfully")
            self.unbind('<Return>')
            self.nuke_frame()
            self.render_mass_uploader()

    def pad_children(self):
        for child in self.frame.winfo_children():
            child.grid_configure(padx=5, pady=5)

    def print_log(self, message):
        self.log.configure(state="normal")
        self.log.insert(tk.END, f"{message}\n")
        self.log.configure(state="disabled")

    def nuke_frame(self):
        for child in self.frame.winfo_children():
            child.destroy()

    def render_mass_uploader(self):
        # this is where the cancer begins
        ttk.Label(self.frame, text="Manga IDs").grid(row=0, column=0)
        ttk.Label(self.frame, text="Volumes").grid(row=1, column=0)
        ttk.Label(self.frame, text="Chapters").grid(row=2, column=0)
        ttk.Label(self.frame, text="Tiles").grid(row=3, column=0)
        # TODO add language validation
        # TODO trim shit and remove empty strings
        ttk.Label(self.frame, text="Languages").grid(row=4, column=0)
        ttk.Label(self.frame, text="Group 1 IDs").grid(row=5, column=0)
        ttk.Label(self.frame, text="Group 2 IDs").grid(row=6, column=0)
        ttk.Label(self.frame, text="Group 3 IDs").grid(row=7, column=0)
        ttk.Label(self.frame, text="Group 4 IDs").grid(row=8, column=0)
        ttk.Label(self.frame, text="Group 5 IDs").grid(row=9, column=0)
        ttk.Label(self.frame, text="Files").grid(row=10, column=0)

        manga_ids = tk.Text(self.frame, height=2, width=40)
        manga_ids.grid(row=0, column=1)
        volumes = tk.Text(self.frame, height=2, width=40)
        volumes.grid(row=1, column=1)
        chapters = tk.Text(self.frame, height=2, width=40)
        chapters.grid(row=2, column=1)
        titles = tk.Text(self.frame, height=2, width=40)
        titles.grid(row=3, column=1)
        languages = tk.Text(self.frame, height=2, width=40)
        languages.grid(row=4, column=1)
        group_1_ids = tk.Text(self.frame, height=2, width=40)
        group_1_ids.grid(row=5, column=1)
        group_2_ids = tk.Text(self.frame, height=2, width=40)
        group_2_ids.grid(row=6, column=1)
        group_3_ids = tk.Text(self.frame, height=2, width=40)
        group_3_ids.grid(row=7, column=1)
        group_4_ids = tk.Text(self.frame, height=2, width=40)
        group_4_ids.grid(row=8, column=1)
        group_5_ids = tk.Text(self.frame, height=2, width=40)
        group_5_ids.grid(row=9, column=1)
        files = []
        ttk.Button(self.frame,
                   text="choose files",
                   command=lambda: self.pick_files(files)).grid(row=10, column=1)

        def start_upload():
            if len(files) == 0:
                self.print_log("nothing to upload")
                return
            upload_button.configure(state="disabled")
            upload_fields = {
                "manga": manga_ids,
                "groups_1": group_1_ids,
                "groups_2": group_2_ids,
                "groups_3": group_3_ids,
                "groups_4": group_4_ids,
                "groups_5": group_5_ids,
                "title": titles,
                "volume": volumes,
                "chapter": chapters,
                "translatedLanguage": languages,
            }
            # extract and split strings
            upload_fields = {key: field.get("1.0", "end-1c").split("\n") for key, field in upload_fields.items()}
            # clip longer fields to number of files selected
            upload_fields = {key: field[:len(files)] for key, field in upload_fields.items()}
            # trim fields and replace empty strings with None
            upload_fields = {key: [None if element.strip() == "" else element.strip() for element in field] for key, field in upload_fields.items()}
            # repeat single input fields
            upload_fields = {key: (field * len(files) if len(field) == 1 else field) for key, field in upload_fields.items()}
            # pad shorter fields with None or pandas will cry
            _ = {key: field.extend([None] * (len(files) - len(field))) for key, field in upload_fields.items()}
            upload_fields["groups"] = list(zip(upload_fields.pop("groups_1"),
                                               upload_fields.pop("groups_2"),
                                               upload_fields.pop("groups_3"),
                                               upload_fields.pop("groups_4"),
                                               upload_fields.pop("groups_5")))
            upload_fields["file"] = files


            chapter_df = pd.DataFrame(upload_fields)
            for idx, chapter in enumerate(chapter_df.itertuples()):
                try:
                    self.mangadex.upload_chapter(chapter)
                except Exception as e:
                    self.print_log(f"{idx + 1}/{len(files)} - {e}")
                else:
                    self.print_log(f"{idx + 1}/{len(files)} - success")
            upload_button.configure(state="normal")
            # TODO clear fields after upload and add clear button

        upload_button = ttk.Button(self.frame,
                                   text="start upload",
                                   command=lambda: start_upload())
        upload_button.grid(row=10, column=2)

        self.pad_children()

    @staticmethod
    def pick_files(file_list):
        new_files = filedialog.askopenfiles(filetypes=[("Zip", "*.zip"), ("Comic Book Zip", ".cbz")])
        if len(new_files) > 0:
            del file_list[:]
            file_list.extend(new_files)


if __name__ == '__main__':
    MassUploader().mainloop()
