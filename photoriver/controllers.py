#!python

class BasicController(object):
    def __init__(self, receiver, uploaders, filters=[]):
        self.receiver = receiver
        self.filters = filters
        self.uploaders = uploaders
        
        self._processed = {}
    
    def process_all(self):
        photos = self.receiver.get_list()
        
        for file_name, photo in photos.iteritems():
            if file_name not in self._processed:
                photo = self.receiver.download_file(file_name)
                for afilter in self.filters:
                    if photo.enabled:
                        photo = afilter.filter(photo)
                for uploader in self.uploaders:
                    if photo.enabled:
                        uploader.upload(photo)
                self._processed[file_name] = photo
