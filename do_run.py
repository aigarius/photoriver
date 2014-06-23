#!python

import time
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

from photoriver.receivers import FlashAirReceiver
from photoriver.controllers import BasicController
from photoriver.uploaders import FlickrUploader, GPlusUploader

logging.info("Starting test")

receiver = FlashAirReceiver("http://192.168.1.100/")
uploader1 = FlickrUploader("Test 123")
uploader2 = GPlusUploader("Test 123")
controller = BasicController(receiver=receiver, uploaders=[uploader1, uploader2])
while(True):
    controller.process_all()
    time.sleep(1)
