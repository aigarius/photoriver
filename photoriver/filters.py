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
        self.gpshistory[datetime.now().replace(microsecond=0)] = kwargs

    def on_status(self, *args, **kwargs):
        self.status_history[datetime.now().replace(microsecond=0)] = kwargs

    def select_location(self, adate):
        adate = adate.replace(microsecond=0)
        dates = sorted(self.gpshistory.keys())
        if not dates or adate < dates[0]:
            return None

        if adate in dates:
            return self.gpshistory[adate]

        if len(dates) == 1 or adate > dates[-1]:
            return self.gpshistory[dates[-1]]

        # Select the two time points bracketing adate from the dates list
        i, j = [(x, x+1) for x in range(0, len(dates)) if dates[x] <= adate and dates[x+1] > adate][0]
        early = dates[i]
        late = dates[j]

        full_interval = (late - early).seconds
        adate_interval = (adate - early).seconds

        if adate_interval <= 0.9 * full_interval:  # 90% of the interval between valid GPS locations is mapped to the earlier location
            return self.gpshistory[early]
        else:
            return self.gpshistory[late]

    def filter(self, photo):
        exif = pexif.JpegFile.fromFile(photo._cached_file)
        primary = exif.get_exif().get_primary()

        agps = self.select_location(datetime.strptime(primary.DateTime, "%Y:%m:%d %H:%M:%S"))
        logger.debug("GPS Location for %s set to: %s, %s", photo.file_name, lat, lon)
        if agps:
            exif.set_geo(agps['lat'], agps['lon'])
            exif.writeFile(photo._cached_file)

        return photo
