#!python

import flickrapi
import shutil
import os.path
import six

from io import open

import logging

logger = logging.getLogger(__name__)


class FolderUploader(object):
    def __init__(self, destination):
        self.destination = destination
        if not os.path.exists(self.destination):
            os.mkdir(self.destination)

    def upload(self, photo):
        with open(os.path.join(self.destination, photo.file_name), "w") as dst:
            with photo.open_file() as src:
                shutil.copyfileobj(src, dst)


class FlickrUploader(object):
    def __init__(self, set_name):
        key = u"26a60d41603c1949a189f898f67d3247"
        secret = u"3de835ffcefadd36"
        self.api = flickrapi.FlickrAPI(key, secret)
        if not self.api.token_valid(perms=u'write'):
            # Get a request token
            self.api.get_request_token(oauth_callback='oob')

            authorize_url = self.api.auth_url(perms=u'write')
            print("Open this URL to authorize: ", authorize_url)

            # Get the verifier code from the user.
            verifier = unicode(six.moves.input('Verifier code: '))

            # Trade the request token for an access token
            self.api.get_access_token(verifier)

        self.set_name = set_name
        self.set_id = None

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

    def upload(self, photo):
        logger.info("Uploading to Flickr: %s", photo)
        rsp = self.api.upload(photo._cached_file, title=photo.file_name)
        logger.info("Uploading done: %s", photo)
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
