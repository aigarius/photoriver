import kivy
kivy.require('1.0.6')

from kivy.app import App
from android import AndroidService


class PhotoRiverApp(App):
    def on_start(self):
        self.service = AndroidService()

    def start_service(self):
        self.service.start()

    def stop_service(self):
        self.service.stop()

    def on_pause(self):
        return True

    def on_resume(self):
        return True


app = PhotoRiverApp()
if __name__ == '__main__':
    app.run()
