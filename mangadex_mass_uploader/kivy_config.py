import os
import sys

os.environ["KIVY_HOME"] = os.path.expanduser("~/.md_mass_uploader")
if hasattr(sys, "_MEIPASS"):
    os.environ["KIVY_NO_CONSOLELOG"] = "1"

from kivy.config import Config
from kivy.resources import resource_add_path

if hasattr(sys, "_MEIPASS"):
    resource_add_path(os.path.join(sys._MEIPASS))

# first time init
if not Config.get("mass_uploader", "initialized", fallback=False):
    os.makedirs(f"{os.environ['KIVY_HOME']}/logins", exist_ok=True)
    os.makedirs(f"{os.environ['KIVY_HOME']}/edits", exist_ok=True)
    if "mass_uploader" not in Config.sections():
        Config.add_section("mass_uploader")
    Config.set("mass_uploader", "initialized", True)
    Config.set("kivy", "desktop", 1)
    Config.set("kivy", "exit_on_escape", 0)
    Config.set("graphics", "window_state", "maximized")
    Config.write()
