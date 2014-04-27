import time
import os
import sys
import logging
import json
from jnius import autoclass

os.chdir("..")
sys.path.append(".")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

from photoriver.receivers import FlashAirReceiver
from photoriver.controllers import BasicController
from photoriver.uploaders import FlickrUploader, GPlusUploader

logging.info("Starting PhotoRiver Service")
service_args = json.loads(os.getenv("PYTHON_SERVICE_ARGUMENT", ""))
if not service_args:
    service_args = dict(
        flashair_uri="http://192.168.10.144/",
        album_name="Test 345",
    )
logging.info("Got args: %s", str(service_args))
activity = autoclass('org.renpy.android.PythonService').mService

pm = activity.getSystemService('power')
lock = pm.newWakeLock(1, "PhotoServiceLock")
lock.acquire()

receiver = FlashAirReceiver(service_args['flashair_uri'])
#uploader1 = FlickrUploader(service_args['album_name'])
uploader2 = GPlusUploader(service_args['album_name'])
controller = BasicController(receiver=receiver, uploaders=[uploader2])

while True:
    controller.process_all()
    time.sleep(5)
