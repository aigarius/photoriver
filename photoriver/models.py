#!python

import os
import os.path

from io import open


class Photo(object):
    def __init__(self, file_name, dirname=".", size=None, timestamp=None):
        self.file_name = file_name
        self.dirname = dirname
        self.size = size
        self.timestamp = timestamp
        self.upload_id = None
        self._cached_file = None
        self._downloaded = False
        self.enabled = True

        cache_name = os.path.join(".cache", file_name)
        if os.path.exists(cache_name) and os.path.getsize(cache_name) == int(size):
            self._downloaded = True
            self._cached_file = cache_name

    def __repr__(self):
        return "Photo({}/{})".format(self.dirname, self.file_name)

    def clean(self):
        if self._downloaded:
            os.remove(self._cached_file)
            self._downloaded = False

    def open_file(self):
        if self._downloaded:
            return open(self._cached_file)
        else:
            return None
