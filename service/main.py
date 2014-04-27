import time
import os
import sys
import logging
from jnius import autoclass

os.chdir("..")
sys.path.append(".")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

from photoriver.receivers import FlashAirReceiver
from photoriver.controllers import BasicController
from photoriver.uploaders import FlickrUploader, GPlusUploader

logging.info("Starting test")
activity = autoclass('org.renpy.android.PythonService').mService

pm = activity.getSystemService('power')
lock = pm.newWakeLock(1, "PhotoServiceLock")
lock.acquire()

receiver = FlashAirReceiver("http://192.168.10.144/")
#uploader1 = FlickrUploader("Test 345")
uploader2 = GPlusUploader("Test 345")
controller = BasicController(receiver=receiver, uploaders=[uploader2])

while True:
    controller.process_all()
    time.sleep(5)
