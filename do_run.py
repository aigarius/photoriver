#!python

import time
import logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(name)s %(levelname)s %(message)s")

from photoriver.receivers import FlashAirReceiver
from photoriver.controllers import BasicController
from photoriver.uploaders import FlickrUploader, GPlusUploader

logging.info("Starting test")

receiver = FlashAirReceiver("http://192.168.10.144/")
uploader1 = FlickrUploader("Test 345")
uploader2 = GPlusUploader("Test 345")
controller = BasicController(receiver=receiver, uploaders=[uploader1, uploader2])
while(True):
    controller.process_all()
    time.sleep(1)
