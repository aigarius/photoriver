#!python

class Photo(object):
    def __init__(self, file_name):
        self.file_name = file_name
        self._cached_file = None
        self._downloaded = False
        self.enabled = True
    
    def open_file(self):
        if self._downloaded:
            return open(self._cached_file)
        else:
            return False
