#!python

class Photo(object):
    def __init__(self, file_name, dirname=None, size=None, timestamp=None):
        self.file_name = file_name
        self.dirname = dirname
        self.size = size
        self.timestamp = timestamp
        self._cached_file = None
        self._downloaded = False
        self.enabled = True
    
    def __repr__(self):
        return "Photo({}/{})".format(self.dirname, self.file_name)
    
    def open_file(self):
        if self._downloaded:
            return open(self._cached_file)
        else:
            return None
