import kivy
import json
kivy.require('1.0.6')

from kivy.app import App
from android import AndroidService


class PhotoRiverApp(App):
    flashair_uri = "http://192.168.10.144/"
    album_name = ""

    def on_start(self):
        self.service = AndroidService()

    def start_service(self):
        service_args = dict(
            flashair_uri=self.flashair_uri,
            album_name=self.album_name,
        )
        self.service.start(json.dumps(service_args))

    def stop_service(self):
        self.service.stop()

    def on_pause(self):
        return True

    def on_resume(self):
        return True


app = PhotoRiverApp()
if __name__ == '__main__':
    app.run()
