#!python
import logging
import fractions

from datetime import datetime

import pexif
from plyer import gps, notification

logger = logging.getLogger(__name__)


class GPSTagFilter(object):
    def __init__(self):
        self.gpshistory = {}
        self.status_history = {}

    def start(self):
        self.gps = gps
        self.gps.configure(
            on_location=self.on_location,
            on_status=self.on_status,
        )
        self.gps.start()

    def on_location(self, *args, **kwargs):
        logger.info("******* GPS Location *** %s *** %s *********", str(args), str(kwargs))
        notification.notify("GSP lat:{0}, lon:{1}".format(kwargs['lat'], kwargs['lon']))
        self.gpshistory[datetime.now()] = kwargs

    def on_status(self, *args, **kwargs):
        logger.info("******* GPS Status *** %s *** %s *********", str(args), str(kwargs))
        self.status_history[datetime.now()] = kwargs

    def select_location(adate):
        return self.gpshistory.values()[-1]

    def filter(self, photo):
        logger.info("GPS HISTORY: " + str(self.gpshistory))
        logger.info("STATUS HISTORY: " + str(self.status_history))
        exif = pexif.JpegFile.fromFile(photo._cached_file)
        primary = exif.get_exif().get_primary()
        logger.info("Primary DateTime : %s", primary.DateTime)
        logger.info("Extended DateTimeOriginal : %s", primary.ExtendedEXIF.DateTimeOriginal)

        agps = self.select_location(primary.DateTime)
        exif.set_geo(agps['lat'], agps['lon'])
        exif.writeFile(photo._cached_file)

        return photo
