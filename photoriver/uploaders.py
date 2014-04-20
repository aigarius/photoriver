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

        self.api = flickrapi.FlickrAPI(key, secret, store_token=False)
        if self._read_cache_token():
            self.api.token_cache.token = self.access_token

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
        self.uploaded_photos = {}
        rsp = self.api.photosets_getList()
        self.set_id = self._find_set(rsp, self.set_name)
        if self.set_id:
            self.uploaded_photos = self._get_photos_from_set(self.set_id)

    def _get_photos_from_set(self, set_id):
        walker = self.api.walk_set(set_id)
        uploaded_photos = {}
        for photo in walker:
            uploaded_photos[photo.get("title")] = {'id': photo.get('id')}
        return uploaded_photos

    def _read_cache_token(self):
        if not os.path.exists("token.cache"):
            return False
        cache = {}
        with open("token.cache", "rb") as f:
            try:
                cache = json.loads(f.read().decode("utf8"))
            except:
                pass
        if "flickr_token" in cache:
            self.access_token = flickrapi.auth.FlickrAccessToken(
                token=cache.get("flickr_token", None),
                token_secret=cache.get("flickr_token_secret", None),
                access_level=cache.get("flickr_access_level", None),
                fullname=cache.get("flickr_fullname", None),
                username=cache.get("flickr_username", None),
                user_nsid=cache.get("flickr_user_nsid", None),
            )
            return True

    def _write_cache_token(self):
        cache = {}
        if os.path.exists("token.cache"):
            with open("token.cache", "rb") as f:
                try:
                    cache = json.loads(f.read().decode("utf8"))
                except:
                    pass
        cache["flickr_token"] = self.access_token.token
        cache["flickr_token_secret"] = self.access_token.token_secret
        cache["flickr_access_level"] = self.access_token.access_level
        cache["flickr_fullname"] = self.access_token.fullname
        cache["flickr_username"] = self.access_token.username
        cache["flickr_user_nsid"] = self.access_token.user_nsid
        with open("token.cache", "wb") as f:
            f.write(json.dumps(cache).encode("utf8"))

    def _upload(self, photo):
        if self.set_id and photo.file_name in self.uploaded_photos:
            logger.info("Already uploaded to Flickr, skipping: %s", photo)
        else:
            logger.info("Uploading to Flickr: %s", photo)
            rsp = self.api.upload(photo._cached_file, title=photo.file_name)
            logger.info("Uploading to Flickr done: %s", photo)
            photo_id = self._get_photo_id_from_rsp(rsp)
            photo.upload_id = photo_id
            if not self.set_id:
                logger.debug("Creating a new set")
                rsp = self.api.photosets_create(title=self.set_name, primary_photo_id=photo_id)
                self.set_id = self._get_set_id_from_rsp(rsp)
            else:
                logger.debug("Adding photo to set")
                self.api.photosets_addPhoto(photoset_id=self.set_id, photo_id=photo_id)
            self.uploaded_photos[photo.file_name] = photo

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
        self.uploaded_photos = self.api.get_photos(self.album["id"])
        logger.info("Using album with id (%s) - %s photos found", self.album["id"], len(self.uploaded_photos.keys()))

    def _upload(self, photo):
        if photo.file_name in self.uploaded_photos:
            logger.info("Already uploaded to G+, skipping: %s", photo)
        else:
            logger.info("Uploading to G+: %s", photo)
            self.api.upload(photo._cached_file, photo.file_name, self.album["id"])
            self.uploaded_photos[photo.file_name] = photo
            logger.info("Uploading to G+ done: %s", photo)
