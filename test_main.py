import unittest
import os
import sqlite3
from main import Data, humanize_size

class TestData(unittest.TestCase):
    def setUp(self):
        # Create a temporary in-memory database for testing
        self.conn = sqlite3.connect(':memory:')
        self.data = Data(db_connection=self.conn)

    def tearDown(self):
        # Close the database connection
        self.conn.close()

    def test_isfilename(self):
        # Test that a new filename is not in the database
        self.assertFalse(self.data.isfilename('test_file.mp4'))

        # Add the filename and test that it's now in the database
        self.data.addfilename('test_file.mp4')
        self.assertTrue(self.data.isfilename('test_file.mp4'))

    def test_delfilename(self):
        # Add a filename and verify it's in the database
        self.data.addfilename('test_file.mp4')
        self.assertTrue(self.data.isfilename('test_file.mp4'))

        # Delete the filename and verify it's no longer in the database
        self.data.delfilename('test_file.mp4')
        self.assertFalse(self.data.isfilename('test_file.mp4'))

class TestHumanizeSize(unittest.TestCase):
    def test_zero_bytes(self):
        self.assertEqual(humanize_size(0), "0 B")

    def test_bytes(self):
        self.assertEqual(humanize_size(500), "500.00 B")

    def test_kilobytes(self):
        self.assertEqual(humanize_size(1024), "1.00 KB")
        self.assertEqual(humanize_size(1500), "1.46 KB")

    def test_megabytes(self):
        self.assertEqual(humanize_size(1048576), "1.00 MB")
        self.assertEqual(humanize_size(2097152), "2.00 MB")

    def test_gigabytes(self):
        self.assertEqual(humanize_size(1073741824), "1.00 GB")

if __name__ == '__main__':
    unittest.main()
