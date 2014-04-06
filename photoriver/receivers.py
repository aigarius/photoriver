#!python

import os
import os.path
import shutil

from photoriver.models import Photo

class BaseReceiver(object):
    def __init__(self, source):
        self.source = source
        self._files = {}
        self._cache_dir = '.cache'
        if not os.path.exists(self._cache_dir):
            os.mkdir(self._cache_dir)
    
    def is_available(self):
        return False
    
    def get_list(self):
        return {}
    
    def download_file(self, name):
        return None

class FolderReceiver(BaseReceiver):
    def __init__(self, source):
        super(FolderReceiver, self).__init__(source)
    
    def is_available(self):
        return os.path.exists(self.source)
    
    def get_list(self):
        if self.is_available():
            files = os.listdir(self.source)
            for file_name in files:
                if file_name not in self._files:
                    self._files[file_name] = Photo(file_name)
        return self._files
    
    def download_file(self, name):
        photo = self._files[name]
        if photo._downloaded:
            return photo
        shutil.copyfile(
            os.path.join(self.source, name),
            os.path.join(self._cache_dir, name)
        )
        photo._downloaded = True
        photo._cached_file = os.path.join(self._cache_dir, name)
        return photo

