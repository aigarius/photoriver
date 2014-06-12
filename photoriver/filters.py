#!python
import logging
import fractions

from datetime import datetime

import pexif
from plyer import gps, notification

logger = logging.getLogger(__name__)


class GPSTagFilter(object):
    def __init__(self):
        self.gps = gps
        self.gps.configure(
            on_location=self.on_location,
            on_status=self.on_status,
        )
        self.history = {}
        self.status_history = {}
        self.gps.start()

    def on_location(self, *args, **kwargs):
        logger.info("******* GPS Location *** %s *** %s *********", str(args), str(kwargs))
        notification.notify("GSP lat:{0}, lon:{1}".format(kwargs['lat'], kwargs['lon']))
        self.history[datetime.now()] = kwargs

    def on_status(self, *args, **kwargs):
        logger.info("******* GPS Status *** %s *** %s *********", str(args), str(kwargs))
        self.status_history[datetime.now()] = kwargs

    def filter(self, photo):
        logger.info("GPS HISTORY: " + str(self.history))
        logger.info("STATUS HISTORY: " + str(self.status_history))
        exif = pexif.JpegFile.fromFile(photo._cached_file)
        primary = exif.get_exif().get_primary()
        logger.info("Primary DateTime : %s", primary.DateTime)
        logger.info("Extended DateTimeOriginal : %s", primary.ExtendedEXIF.DateTimeOriginal)

        agps = self.history.get(max(self.history.keys()))
        exif.set_geo(agps['lat'], agps['lon'])
        exif.writeFile(photo._cached_file)

        return photo
