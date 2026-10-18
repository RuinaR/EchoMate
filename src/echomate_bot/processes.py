"""Options for noninteractive child commands launched by the desktop app."""
import os
import subprocess


def background_options():
    # Capturing stdout alone does not suppress a console under pythonw on Windows.
    return {'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
