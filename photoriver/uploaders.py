#!python

import flickrapi
import shutil
import os.path

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
        key = "26a60d41603c1949a189f898f67d3247"
        secret = "3de835ffcefadd36"
        self.api = flickrapi.FlickrAPI(key, secret)
        (token, frob) = self.api.get_token_part_one(perms='write')
        if not token:
            raw_input('Press ENTER after you authorized this program')
        self.api.get_token_part_two((token, frob))
        
        self.set_name = set_name
        self.set_id = None

    def _add_to_set(self, photo_id):
        if not self.set_id:
            rsp = self.api.photosets_getList()
            self.set_id = self._find_set(rsp, self.set_name)
        if not self.set_id:
            rsp = self.api.photosets_create(name=self.set_name, primary_photo_id=photo_id)
            self.set_id = self._get_set_id_from_rsp(rsp)
        else:
            return self.api.photosets_addPhoto(photoset_id=self.set_id, photo_id=photo_id)
    
    def upload(self, photo):
        rsp = self.api.upload(photo._cached_file, title=photo.file_name)
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
