import unittest
import os
import dotenv
from unittest.mock import patch, MagicMock
from main import Shows

class TestShows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Load environment variables from .env file
        dotenv.load_dotenv()
        
    def setUp(self):
        # Save original environment variables
        self.original_env = {
            'twitcluburl': os.environ.get('twitcluburl'),
            'twitclubblocksize': os.environ.get('twitclubblocksize'),
            'twitclubdestination': os.environ.get('twitclubdestination')
        }
        
        # Set test environment variables
        os.environ['twitcluburl'] = 'https://test.example.com/rss?auth=test_token'
        os.environ['twitclubblocksize'] = '2097152'  # 2MB
        os.environ['twitclubdestination'] = './test_downloads'
        
    def tearDown(self):
        # Restore original environment variables
        for key, value in self.original_env.items():
            if value is not None:
                os.environ[key] = value
            elif key in os.environ:
                del os.environ[key]
    
    @patch('requests.get')
    def test_shows_initialization(self, mock_get):
        # Mock the response from requests.get
        mock_response = MagicMock()
        mock_response.text = '<rss><channel><item></item></channel></rss>'
        mock_get.return_value = mock_response
        
        # Create Shows instance
        shows = Shows()
        
        # Check that environment variables were correctly read
        self.assertEqual(shows.url, 'https://test.example.com/rss?auth=test_token')
        self.assertEqual(shows.blocksize, 2097152)
        self.assertEqual(shows.twitclubdestination, './test_downloads')
        
    @patch('requests.get')
    def test_shows_with_env_file(self, mock_get):
        """Test Shows class using environment variables from .env file"""
        # Load variables from .env file
        dotenv.load_dotenv()
        
        # Mock the response from requests.get
        mock_response = MagicMock()
        mock_response.text = '<rss><channel><item></item></channel></rss>'
        mock_get.return_value = mock_response
        
        # Create Shows instance
        shows = Shows()
        
        # Check that environment variables were correctly read
        self.assertIsNotNone(shows.url)
        self.assertIsNotNone(shows.blocksize)
        self.assertIsNotNone(shows.twitclubdestination)
        
if __name__ == '__main__':
    unittest.main()