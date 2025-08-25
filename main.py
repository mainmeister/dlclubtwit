import argparse
import os
import pathlib
import shutil
import sys
import xml.etree.ElementTree as ET
import sqlite3
import requests
from html2txt import converters

# Get command line arguments
def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Process command-line arguments.")
    parser.add_argument("-s", "--skip", action="store_true", help="Skip already downloaded files.")
    return parser.parse_args()

# Manage the database for downloaded files
class Data:
    """Manages a single database table to track downloaded filenames."""

    def __init__(self, db_path='dltwit.sqlite'):
        """Create the database and 'file' table if they don't exist."""
        sql_create = """
        CREATE TABLE IF NOT EXISTS file (filename TEXT UNIQUE);
        """
        self.conn = sqlite3.connect(db_path)
        self.conn.executescript(sql_create)

    def is_filename(self, filename):
        """Check if a filename exists in the database."""
        sql_select = "SELECT COUNT(*) FROM file WHERE filename = ?"
        cursor = self.conn.execute(sql_select, (filename,))
        result = cursor.fetchone()
        return result[0] > 0

    def add_filename(self, filename):
        """Add a new filename to the database."""
        sql_insert = "INSERT INTO file (filename) VALUES (?);"
        try:
            self.conn.execute(sql_insert, (filename,))
            self.conn.commit()
        except sqlite3.IntegrityError:
            # Handle case where the filename already exists (e.g., race condition)
            print(f"Warning: Filename '{filename}' already exists in the database.")

    def del_filename(self, filename):
        """Delete a filename from the database."""
        sql_delete = "DELETE FROM file WHERE filename = ?"
        self.conn.execute(sql_delete, (filename,))
        self.conn.commit()

# Represents a single show/episode
class Show:
    def __init__(self, title, description, pub_date, url, url_length, url_type, destination):
        self.title = self.clean_title(title)
        self.description = description
        self.pub_date = pub_date
        self.url = url
        self.url_length = url_length
        self.url_type = url_type
        self.filename = f"{self.title}.mp4"
        self.output_path = pathlib.Path(destination) / self.filename

    @staticmethod
    def clean_title(title):
        """Clean up the title by removing bad characters."""
        bad_characters = r'\\/:.+?*'
        for bad_char in bad_characters:
            title = title.replace(bad_char, '')
        return title.strip()

# Create an object that maintains the list of shows
class Shows:
    """Fetches and parses the TWiT Club XML feed."""
    def __init__(self):
        self.url = os.environ.get('twitcluburl')
        if not self.url:
            raise EnvironmentError("Set environment string 'twitcluburl' to the URL for your TWiT Club stream.")

        self.block_size = int(os.environ.get('twitclubblocksize', 1048576))
        self.destination = os.environ.get('twitclubdestination', pathlib.Path.cwd())
        
        # Request the XML feed and parse it
        try:
            response = requests.get(self.url, timeout=10)
            response.raise_for_status()  # Raise an exception for bad status codes
            self.root = ET.fromstring(response.text)
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Error fetching RSS feed from {self.url}: {e}")

    def get_shows(self):
        """Parses the XML and yields Show objects."""
        for item in self.root.iter('item'):
            title_elem = item.find('title')
            title = title_elem.text.strip() if title_elem is not None and title_elem.text is not None else "Untitled"

            desc_elem = item.find('description')
            if desc_elem is not None and desc_elem.text:
                try:
                    description = converters.Html2Markdown().convert(desc_elem.text)
                except IndexError:
                    description = "Description could not be parsed."
            else:
                description = "No description available."
            
            pub_date_elem = item.find('pubDate')
            pub_date = pub_date_elem.text.strip() if pub_date_elem is not None and pub_date_elem.text is not None else "Unknown date"
            
            enclosure_elem = item.find('enclosure')
            url = enclosure_elem.attrib.get('url', '') if enclosure_elem is not None else ''
            url_length = enclosure_elem.attrib.get('length', '0') if enclosure_elem is not None else '0'
            url_type = enclosure_elem.attrib.get('type', '') if enclosure_elem is not None else ''
            
            yield Show(title, description, pub_date, url, url_length, url_type, self.destination)

def humanize_size(size_bytes):
    """Convert an integer size in bytes to a human-readable format."""
    if size_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    size = float(size_bytes)
    for unit in units:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0

def download_show(show, block_size):
    """Downloads a single show, with progress updates and error handling."""
    if not show.url:
        print(f"Skipping {show.title}: No URL available for this show.")
        return False
    
    print(f"\nTitle: {show.title} ({show.pub_date})")
    print(f"Description: {show.description}")
    
    try:
        url_length_int = int(show.url_length) if show.url_length.isdigit() else 0
        print(f"URL: {show.url}\nSize: {humanize_size(url_length_int)} Type: {show.url_type}")
        print(f"Saving to: {show.output_path}")

        temp_path = pathlib.Path(f'twitclubdownload.tmp')
        
        with requests.get(show.url, stream=True, timeout=30) as r:
            r.raise_for_status()
            bytes_downloaded = 0
            with open(temp_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=block_size):
                    if not chunk:
                        continue
                    f.write(chunk)
                    bytes_downloaded += len(chunk)
                    percentage = (bytes_downloaded / url_length_int * 100) if url_length_int > 0 else 0
                    print(f"Completed {humanize_size(bytes_downloaded)} {percentage:3.2f}%", end='\r', flush=True)
            print() # new line after download progress
        
        # Move the temporary file to the final destination
        shutil.move(str(temp_path), show.output_path)
        return True

    except requests.exceptions.RequestException as e:
        print(f"\nError downloading {show.title} from {show.url}: {e}")
        return False
    except (IOError, OSError) as e:
        print(f"\nError handling file system operation for {show.title}: {e}")
        return False
    except KeyboardInterrupt:
        print("\nDownload interrupted by user. Cleaning up...")
        if temp_path.exists():
            os.remove(temp_path)
        sys.exit(0)

# Main program
if __name__ == '__main__':
    try:
        args = parse_arguments()
        
        # Instantiate objects once outside the loop
        data_manager = Data()
        shows_feed = Shows()

        print(f'Club TWiT URL: {shows_feed.url}\nDestination: {shows_feed.destination}\nBlock Size: {humanize_size(shows_feed.block_size)}\n')
        
        for show in shows_feed.get_shows():
            if data_manager.is_filename(str(show.output_path)):
                print(f"Skipping {show.title}: Already downloaded and in database.")
                continue
            
            if show.output_path.exists():
                print(f"Skipping {show.title}: File already exists on disk.")
                if not args.skip:
                    data_manager.add_filename(str(show.output_path))
                continue
            
            # If not skipped, download the show
            if download_show(show, shows_feed.block_size):
                data_manager.add_filename(str(show.output_path))

    except (EnvironmentError, ConnectionError, KeyboardInterrupt) as e:
        print(f"A fatal error occurred: {e}")
        sys.exit(1)
