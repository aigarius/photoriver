import kivy
kivy.require('1.0.6')  # replace with your current kivy version !

from kivy.app import App
from kivy.uix.label import Label
import logging

import requests
from photoriver import models


from photoriver.receivers import FlashAirReceiver
from photoriver.controllers import BasicController
from photoriver.uploaders import FlickrUploader, GPlusUploader

logging.info("Starting test")

print(1)
receiver = FlashAirReceiver("http://192.168.10.144/")
print(2)
uploader1 = FlickrUploader("Test 345")
print(3)
uploader2 = GPlusUploader("Test 345")
print(4)
controller = BasicController(receiver=receiver, uploaders=[uploader1, uploader2])
print(5)
controller.process_all()
controller.process_all()
controller.process_all()


class MyApp(App):

    def build(self):
        return Label(text="Starting up")


if __name__ == '__main__':
    MyApp().run()
