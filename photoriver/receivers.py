#!python

import os
import os.path
import shutil
import requests
import logging

from io import open
from datetime import datetime

from photoriver.models import Photo

logger = logging.getLogger(__name__)


class BaseReceiver(object):
    def __init__(self, source):
        self.source = source
        self._files = {}
        self._cache_dir = '.cache'
        if not os.path.exists(self._cache_dir):
            os.mkdir(self._cache_dir)


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
        photo.size = os.path.getsize(photo._cached_file)
        return photo


class FlashAirReceiver(BaseReceiver):
    def __init__(self, url, folder="/DCIM/102CANON", cid=None, timeout=5):
        super(FlashAirReceiver, self).__init__(source=url)
        self.folder = folder
        self.cid = cid
        self.timeout = timeout

    def is_available(self):
        cid = None
        try:
            r = requests.get(self.source + "command.cgi?op=120", timeout=self.timeout)
            if r.status_code == 200:
                cid = r.text
        except:
            pass

        if cid:
            if self.cid:
                return cid == self.cid
            else:
                self.cid = cid
                return True
        else:
            return False

    def get_list(self):
        r = None
        try:
            r = requests.get(self.source + "command.cgi?op=102", timeout=self.timeout)
        except:
            pass
        if self._files and (not r or r.status_code != 200 or r.text[0] == "0"):
            # We have gotten some data in the past and the card is either unavailable or reports that "nothing has changed"
            return self._files
        try:
            r = requests.get(self.source + "command.cgi?op=100&DIR=" + self.folder, timeout=self.timeout)
        except:
            return self._files
        if r.status_code == 200:
            lines = r.text.split("\n")
            if lines[0].strip() != "WLANSD_FILELIST":
                return self._files

            files = {}
            for line in lines[1:]:
                if not line:
                    continue

                dirname, filename, size, attribute, adate, atime = line.split(',')
                adate = int(adate)
                atime = int(atime)
                timestamp = datetime(
                    ((adate & (0x3F << 9)) >> 9) + 1980,
                    ((adate & (0x0F << 5)) >> 5),
                    adate & (0x1F),
                    ((atime & (0x1F << 11)) >> 11),
                    ((atime & (0x3F << 5)) >> 5),
                    (atime & (0x1F)) * 2
                )
                files[filename] = Photo(filename, dirname=dirname, size=size, timestamp=timestamp)

            if set(files.keys()) != set(self._files.keys()):
                logger.info("New photos found on FlashAir: %s", set(files.keys())-set(self._files.keys()))
                self._files = files
        return self._files

    def download_file(self, name):
        logging.info("Downloading from FlashAir: %s", name)
        photo = self._files[name]
        if photo._downloaded:
            return photo
        r = requests.get(self.source.rstrip('/') + os.path.join(photo.dirname, name))
        with open(os.path.join(self._cache_dir, name), 'wb') as fd:
            for chunk in r.iter_content(1024*1024):
                fd.write(chunk)
        photo._downloaded = True
        photo._cached_file = os.path.join(self._cache_dir, name)
        photo.size = os.path.getsize(photo._cached_file)
        logging.info("Done downloading: %s", name)
        return photo
