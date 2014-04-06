#!python

import shutil
import os.path

class FolderUploader(object):
    def __init__(self, destination):
        self.destination = destination
        if not os.path.exists(self.destination):
            os.mkdir(self.destination)

    def upload(self, photo):
        with open(os.path.join(self.destination, photo.file_name), "w") as dst:
            shutil.copyfileobj(photo.open_file(), dst)
