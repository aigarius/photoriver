#!python

import os.path

from os import mkdir, rename
from shutil import rmtree
from unittest import TestCase
from mock import Mock
from io import StringIO

from photoriver.receivers import FolderReceiver
from photoriver.controllers import BasicController
from photoriver.uploaders import FolderUploader

class BasicTest(TestCase):
    def basic_test(self):
        self.assertTrue(2+2==4)


class ReceiverTest(TestCase):
    def setUp(self):
        mkdir("test_folder")
        self.receiver = FolderReceiver("test_folder/")
    
    def tearDown(self):
        rmtree("test_folder", ignore_errors=True)
    
    def test_nodata(self):
        rmtree("test_folder")
        self.assertEqual(self.receiver.get_list(), {})
        self.assertFalse(self.receiver.is_available())
        mkdir("test_folder")
        self.assertEqual(self.receiver.get_list(), {})
        self.assertTrue(self.receiver.is_available())
    
    def test_add_file(self):
        with open("test_folder/IMG_123.JPG", "w") as f:
            f.write("DUMMY JPEG FILE HEADER")
        
        self.assertEqual(list(self.receiver.get_list().keys()), ['IMG_123.JPG'])
        cached_file = self.receiver.download_file('IMG_123.JPG')
        with cached_file.open_file() as f:
            data = f.read()
        
        self.assertEqual(data, "DUMMY JPEG FILE HEADER")
    
    def test_add_file_offline(self):
        with open("test_folder/IMG_123.JPG", "w") as f:
            f.write("DUMMY JPEG FILE HEADER")
        
        self.assertEqual(list(self.receiver.get_list().keys()), ['IMG_123.JPG'])
        rename("test_folder", "other_folder")
        self.assertEqual(list(self.receiver.get_list().keys()), ['IMG_123.JPG'])

        with open("other_folder/IMG_124.JPG", "w") as f:
            f.write("DUMMY JPEG FILE HEADER 2")

        rename("other_folder", "test_folder")
        self.assertEqual(sorted(self.receiver.get_list().keys()), ['IMG_123.JPG', 'IMG_124.JPG'])

class ControllerTest(TestCase):
    def setUp(self):
        self.receiver = Mock()
        self.filter1 = Mock()
        self.filter2 = Mock()
        self.uploader = Mock()
        self.controller = BasicController(receiver=self.receiver, filters=[self.filter1, self.filter2], uploaders=[self.uploader])
    
    def test_nodata(self):
        self.receiver.get_list.return_value = {}

        self.controller.process_all()
        
        self.receiver.get_list.assert_called_once_with()
        
    def test_basic_filtration(self):
        mock1 = Mock(file_name="IMG_123.JPG")
        mock2 = Mock(file_name="IMG_123.JPG", _cached=True)
        mock3 = Mock(file_name="IMG_123.JPG", _cached=True, gps_data="something")
        mock4 = Mock(file_name="IMG_123.JPG", _cached=True, gps_data="something", title="Dude!")
        self.receiver.get_list.return_value = {'IMG_123.JPG': mock1}
        self.receiver.is_available.return_value = True
        self.receiver.download_file.return_value = mock2
        self.filter1.filter.return_value = mock3
        self.filter2.filter.return_value = mock4
        
        self.controller.process_all()
        
        self.receiver.download_file.assert_called_once_with("IMG_123.JPG")
        self.filter1.filter.assert_called_once_with(mock2)
        self.filter2.filter.assert_called_once_with(mock3)
        self.uploader.upload.assert_called_once_with(mock4)
        
        
class UploaderTest(TestCase):        
    def setUp(self):
        self.uploader = FolderUploader("upload_folder/")
    
    def tearDown(self):
        rmtree("upload_folder", ignore_errors=True)
    
    def test_upload(self):
        photo_obj = Mock(file_name="IMG_123.JPG")
        photo_file = StringIO(u"JPEG DUMMY TEST DATA")
        photo_obj.open_file.return_value = photo_file
        
        self.uploader.upload(photo_obj)
        
        self.assertTrue(os.path.exists("upload_folder/IMG_123.JPG"))
        with open("upload_folder/IMG_123.JPG") as f:
            data = f.read()
        self.assertEqual(data, "JPEG DUMMY TEST DATA")
        
class IntegrationTest(TestCase):
    def tearDown(self):
        rmtree("test_folder", ignore_errors=True)
        rmtree("upload_folder", ignore_errors=True)

    def test_basic_pipeline(self):        
        mkdir("test_folder")
        receiver = FolderReceiver("test_folder/")
        uploader = FolderUploader("upload_folder/")
        with open("test_folder/IMG_123.JPG", "w") as f:
            f.write("DUMMY JPEG FILE HEADER")
                
        controller = BasicController(receiver=receiver, uploaders=[uploader])
        controller.process_all()

        self.assertTrue(os.path.exists("upload_folder/IMG_123.JPG"))
        with open("upload_folder/IMG_123.JPG") as f:
            data = f.read()
        self.assertEqual(data, "DUMMY JPEG FILE HEADER")
        
        
        
        
        
        
        
        
        
