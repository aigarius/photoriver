#!python

import time
import logging

from photoriver.receivers import FlashAirReceiver
from photoriver.controllers import BasicController
from photoriver.uploaders import FlickrUploader

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(name)s %(levelname)s %(message)s")

receiver = FlashAirReceiver("http://192.168.10.144/")
uploader = FlickrUploader("Test 234")
controller = BasicController(receiver=receiver, uploaders=[uploader])
while(True):
    controller.process_all()
    time.sleep(1)
