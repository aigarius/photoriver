#!python

from os import mkdir
from shutil import rmtree
from unittest import TestCase
from mock import Mock

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
        rmtree("test_folder/")
    
    def test_nodata(self):
        rmtree("test_folder/")
        self.assertEqual(self.receiver.get_list(), {})
        self.assertFalse(self.receiver.is_available())
        mkdir("test_folder")
        self.assertEqual(self.receiver.get_list(), {})
        self.assertTrue(self.receiver.is_available())
    
    def test_add_file(self):
        with open("test_folder/IMG_123.JPG", "w") as f:
            f.write("DUMMY JPEG FILE HEADER")
        
        self.assertEqual(self.receiver.get_list().keys(), ['IMG_123.JPG'])
        cached_file = self.receiver.download_file('IMG_123.JPG')
        data = cached_file.open_file().read()
        
        self.assertEqual(data, "DUMMY JPEG FILE HEADER")
    
    def test_add_file_offline(self):
        with open("test_folder/IMG_123.JPG", "w") as f:
            f.write("DUMMY JPEG FILE HEADER")
        
        self.assertEqual(self.receiver.get_list().keys(), ['IMG_123.JPG'])
        rename("test_folder", "other_folder")
        self.assertEqual(self.receiver.get_list().keys(), ['IMG_123.JPG'])

        with open("other_folder/IMG_124.JPG", "w") as f:
            f.write("DUMMY JPEG FILE HEADER 2")

        rename("other_folder", "test_folder")
        self.assertEqual(self.receiver.get_list().keys(), ['IMG_123.JPG', 'IMG_124.JPG'])

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
        first_mock = Mock(file_name="IMG_123.JPG")
        second_mock = Mock(file_name="IMG_123.JPG", gps_data="something")
        third_mock = Mock(file_name="IMG_123.JPG", gps_data="something", title="Dude!")
        self.receiver.get_list.return_value = {'IMG_123.JPG': first_mock}
        self.receiver.is_available.return_value = True
        self.filter1.filter.return_value = second_mock
        self.filter2.filter.return_value = third_mock
        
        self.controller.process_all()
        
        self.filter1.filter.assert_called_once_with(first_mock)
        self.filter2.filter.assert_called_once_with(second_mock)
        self.uploader.upload.assert_called_once_with(third_mock)
        
        
class UploaderTest(TestCase):        
    def setUp(self):
        self.uploader = FolderUploader("upload_folder/")
    
    def tearDown(self):
        rmtree("upload_folder/")
    
    def test_upload(self):
        photo_obj = Mock(file_name="IMG_123.JPG")
        photo_file = Mock()
        photo_obj.open_file.return_value = photo_file
        photo_file.read.return_value = "JPEG DUMMY TEST DATA"
        
        self.uploader.upload(photo_obj)
        
        self.assertTrue(os.path.exists("upload_folder/IMG_123.JPG"))
        data = open("upload_folder/IMG_123.JPG").read()
        self.assertEqual(data, "JPEG DUMMY TEST DATA")
        
class IntegrationTest(TestCase):
    def tearDown(self):
        rmtree("test_folder/")
        rmtree("upload_folder/")

    def test_basic_pipeline(self):        
        mkdir("test_folder")
        receiver = FolderReceiver("test_folder/")
        uploader = FolderUploader("upload_folder/")
        with open("test_folder/IMG_123.JPG", "w") as f:
            f.write("DUMMY JPEG FILE HEADER")
                
        controller = BasicController(receiver=receiver, uploader=uploader)
        self.controller.process_all()

        self.assertTrue(os.path.exists("upload_folder/IMG_123.JPG"))
        data = open("upload_folder/IMG_123.JPG").read()
        self.assertEqual(data, "DUMMY JPEG FILE HEADER")
        
        
        
        
        
        
        
        
        
