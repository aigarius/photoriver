#!python

import flickrapi
import shutil
import os.path
import six
import json

from io import open
from concurrent.futures import ThreadPoolExecutor

from photoriver.gplusapi import GPhoto

import logging

logger = logging.getLogger(__name__)


class BaseUploader(object):
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=5)

    def upload(self, photo):
        return self.executor.submit(self._upload, photo)


class FolderUploader(BaseUploader):
    def __init__(self, destination):
        super(FolderUploader, self).__init__()
        self.destination = destination
        if not os.path.exists(self.destination):
            os.mkdir(self.destination)

    def _upload(self, photo):
        with open(os.path.join(self.destination, photo.file_name), "w") as dst:
            with photo.open_file() as src:
                shutil.copyfileobj(src, dst)


class FlickrUploader(BaseUploader):
    def __init__(self, set_name):
        super(FlickrUploader, self).__init__()
        key = u"26a60d41603c1949a189f898f67d3247"
        secret = u"3de835ffcefadd36"

        if self._read_cache_token():
            self.api = flickrapi.FlickrAPI(key, secret, token=self.access_token, store_token=False)
        else:
            self.api = flickrapi.FlickrAPI(key, secret, store_token=False)

        if not self.api.token_valid(perms=u'write'):
            # Get a request token
            self.api.get_request_token(oauth_callback='oob')

            authorize_url = self.api.auth_url(perms=u'write')

            # Get the verifier code from the user.
            verifier = six.moves.input('URL: {0}\nVerifier code: '.format(authorize_url))

            # Trade the request token for an access token
            self.api.get_access_token(verifier)
        self.access_token = self.api.token_cache.token
        self._write_cache_token()

        self.set_name = set_name
        self.set_id = None

    def _read_cache_token(self):
        if not os.path.exists("token.cache"):
            return False
        cache = {}
        with open("token.cache", "rb") as f:
            try:
                cache = json.load(f)
            except:
                pass
        self.access_token = cache.get("flickr_access_token", None)
        return True

    def _write_cache_token(self):
        cache = {}
        if os.path.exists("token.cache"):
            with open("token.cache", "rb") as f:
                try:
                    cache = json.load(f)
                except:
                    pass
        cache["flickr_access_token"] = self.access_token
        with open("token.cache", "wb") as f:
            f.write(json.dumps(cache).encode("utf8"))

    def _add_to_set(self, photo_id):
        if not self.set_id:
            rsp = self.api.photosets_getList()
            self.set_id = self._find_set(rsp, self.set_name)
        if not self.set_id:
            logger.debug("Creating a new set")
            rsp = self.api.photosets_create(title=self.set_name, primary_photo_id=photo_id)
            self.set_id = self._get_set_id_from_rsp(rsp)
        else:
            logger.debug("Adding photo to set")
            return self.api.photosets_addPhoto(photoset_id=self.set_id, photo_id=photo_id)

    def _upload(self, photo):
        logger.info("Uploading to Flickr: %s", photo)
        rsp = self.api.upload(photo._cached_file, title=photo.file_name)
        logger.info("Uploading to Flickr done: %s", photo)
        photo_id = self._get_photo_id_from_rsp(rsp)
        photo.upload_id = photo_id
        self._add_to_set(photo_id)

    def _find_set(self, rsp, set_name):
        set_id = None
        for aset in rsp.iter("photoset"):
            title = aset.find("title").text
            if title == set_name:
                set_id = aset.attrib['id']
        return set_id

    def _get_set_id_from_rsp(self, rsp):
        return int(rsp.find("photoset").attrib['id'])

    def _get_photo_id_from_rsp(self, rsp):
        return int(rsp.find('photoid').text)


class GPlusUploader(BaseUploader):
    def __init__(self, set_name):
        super(GPlusUploader, self).__init__()
        self.api = GPhoto()
        albums = self.api.get_albums()
        if set_name not in albums:
            logger.info("Creating an album")
            self.api.create_album(set_name)
            albums = self.api.get_albums()
        self.album = albums[set_name]
        logger.info("Using album with id (%s)", self.album["id"])

    def _upload(self, photo):
        logger.info("Uploading to G+: %s", photo)
        self.api.upload(photo._cached_file, photo.file_name, self.album["id"])
        logger.info("Uploading to G+ done: %s", photo)
