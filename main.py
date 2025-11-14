import argparse
import os
import pathlib
import shutil
import sys
import time
import xml.etree.ElementTree as ET
import sqlite3
import requests
from html2txt import converters

# Get the list a command line arguments
def parse_arguments():
    parser = argparse.ArgumentParser(description="Process command-line arguments.")
    parser.add_argument("-s", "--skip", action="store_true", help="Skip already downloaded files.")
    args = parser.parse_args()
    return args

# Manage our one table, named filename, to keep track
# of downloaded or skipped file names
class Data():

    # Create the filename table if it does not already exist
    def __init__(self, db_path='dltwit.sqlite', db_connection=None):
        sql_create = """
        create table if not exists file (filename text unique);
        """
        if db_connection:
            self.data = db_connection
        else:
            self.data = sqlite3.connect(db_path)
        self.data.executescript(sql_create)

    # check if filename exists in the filename table
    # return true if it does
    def isfilename(self, filename):
        sql_select = """
        select count(*) from file where filename=?
        """
        row = self.data.execute(sql_select, (filename,))
        result = row.fetchone()
        return result[0] > 0

    # Add a new filename to the filename table
    def addfilename(self, filename):
        sql_insert ="""
insert into file (filename)
values (?);        """
        self.data.execute(sql_insert, (filename,))
        self.data.commit()

    # Delete a filename from the filename table
    # Not currently used. A future command line option
    # will use this to allow the removal of a name
    def delfilename(self, filename):
        sql_delete = """
        delete from file where filename=?
        """
        self.data.execute(sql_delete, (filename,))
        self.data.commit()

# Create an object that maintains the list of shows.
class Shows():

    # Get the three environment variables
    #   1 the url of this members episodes required (twitcluburl)
    #   2 the block size to use for reading the video
    #     optional default 1048576 (twitclubblocksize)
    #   3 the destination folder optional default ./ (twitclubdestination)
    def __init__(self):
        try:
            self.url = os.environ['twitcluburl']
        except KeyError:
            print('Set environment string twitcluburl to the url for your twitclub stream')
            sys.exit(1)
        try:
            self.blocksize = int(os.environ['twitclubblocksize'])
        except KeyError:
            self.blocksize = 1048576
        try:
            self.twitclubdestination = os.environ['twitclubdestination']
        except KeyError:
            self.twitclubdestination = os.path.abspath('./')
        # Request the xml feed and parse it
        r = requests.get(self.url)
        self.root = ET.fromstring(r.text)

    # Objectify the XML structure
    def shows(self):
        for show in self.root.iter('item'):
            description_element = show.find('description')
            if description_element is not None and description_element.text is not None:
                try:
                    self.description = converters.Html2Markdown().convert(description_element.text)
                except IndexError:
                    # Handle the IndexError that occurs in the html2txt parser
                    self.description = "Description could not be parsed"
            else:
                self.description = "No description available"

            # Handle title element
            title_element = show.find('title')
            if title_element is not None and title_element.text is not None:
                self.title = self.cleanTitle(title_element.text)
            else:
                self.title = "Untitled"

            # Handle pubDate element
            pubDate_element = show.find('pubDate')
            if pubDate_element is not None and pubDate_element.text is not None:
                self.pubDate = pubDate_element.text
            else:
                self.pubDate = "Unknown date"

            # Handle enclosure element and its attributes
            self.enclosure = show.find('enclosure')
            if self.enclosure is not None:
                try:
                    self.url = self.enclosure.attrib.get('url', '')
                    self.urllength = self.enclosure.attrib.get('length', '0')
                    self.urltype = self.enclosure.attrib.get('type', '')
                except (KeyError, AttributeError):
                    self.url = ''
                    self.urllength = '0'
                    self.urltype = ''
            else:
                self.url = ''
                self.urllength = '0'
                self.urltype = ''

            self.filename = self.title + '.mp4'
            self.outputFilename = os.path.join(self.twitclubdestination, self.filename)
            self.downloadfilename = os.path.join(self.twitclubdestination, 'twitclubdownload')
            yield show

    # Clean up the title of the show by removing bad characters
    def cleanTitle(self, title):
        newTitle = str(title)
        badCharacters = '\\/:.+?*'
        for badCharacter in badCharacters:
            newTitle = newTitle.replace(badCharacter, '')
        return newTitle

# Make the size of the show a human friendly string
# returns a string with 2 decimals places and a unit
def humanize_size(size_bytes):
    """
    Convert an integer size in bytes to a human-readable format.
    """
    if size_bytes == 0:
        return "0 B"

    # Define units
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    size_in_kb = size_bytes
    unit_index = 0

    # Divide by 1024 to find the right unit
    while size_in_kb >= 1024 and unit_index < len(units) - 1:
        size_in_kb /= 1024
        unit_index += 1

    # Format with f-string and only show 2 decimal places
    return f"{size_in_kb:.2f} {units[unit_index]}"

# Resumable downloader: continues where it left off until complete
def download_with_resume(url, temp_path, final_path, blocksize, total_length=None, max_retries=8):
    """
    Download a file with resume support using HTTP Range.

    - Writes to temp_path; when complete, moves to final_path atomically.
    - If an error occurs, it will retry and continue from the last written byte.
    - KeyboardInterrupt leaves the partial file for later resumption.

    Returns True when the final file is fully written, False otherwise.
    """
    # Ensure destination directory exists
    dest_dir = os.path.dirname(final_path) or "."
    os.makedirs(dest_dir, exist_ok=True)

    # If final file already exists, nothing to do
    if os.path.exists(final_path):
        return True

    # Track progress
    bytes_done = os.path.getsize(temp_path) if os.path.exists(temp_path) else 0

    # If total_length is provided as string, coerce to int or None
    if isinstance(total_length, str):
        total_length = int(total_length) if total_length.isdigit() else None

    attempt = 0
    try:
        while True:
            # If total length known and we already have it, finish
            if total_length is not None and bytes_done >= total_length > 0:
                # Move into place
                shutil.move(temp_path, final_path)
                return True

            headers = {}
            if bytes_done > 0:
                headers["Range"] = f"bytes={bytes_done}-"

            try:
                with requests.get(url, stream=True, headers=headers, timeout=60) as resp:
                    # If server doesn't honor range and returns 200 while we have partial, restart
                    if bytes_done > 0 and resp.status_code == 200:
                        # Start fresh: discard partial
                        os.remove(temp_path)
                        bytes_done = 0
                    # Accept 200 (fresh) or 206 (partial)
                    if resp.status_code not in (200, 206):
                        raise requests.RequestException(f"Unexpected status {resp.status_code}")

                    # Decide total size if not known
                    if total_length is None:
                        # Prefer Content-Range when 206, else Content-Length
                        cr = resp.headers.get("Content-Range")
                        if cr and "/" in cr:
                            try:
                                total_length = int(cr.split("/")[-1])
                            except ValueError:
                                total_length = None
                        else:
                            try:
                                total_length = int(resp.headers.get("Content-Length")) if resp.headers.get("Content-Length") else None
                                if bytes_done and total_length is not None:
                                    total_length += bytes_done
                            except (TypeError, ValueError):
                                total_length = None

                    mode = "ab" if bytes_done > 0 else "wb"
                    with open(temp_path, mode) as fd:
                        for chunk in resp.iter_content(chunk_size=blocksize):
                            if not chunk:
                                continue
                            fd.write(chunk)
                            bytes_done += len(chunk)

                            # Progress output
                            if total_length and total_length > 0:
                                pct = (bytes_done / float(total_length)) * 100.0
                            else:
                                pct = 0.0
                            print(
                                f"completed {humanize_size(bytes_done)} "
                                f"{pct:3.2f}%                    ",
                                end='\r', flush=True
                            )

                # Completed this request without exception; check if done or loop again
                if total_length is None:
                    # If server didn't provide a total, we assume completion when stream closes
                    # Move temp into place and finish
                    shutil.move(temp_path, final_path)
                    print()  # newline after progress
                    return True

                if bytes_done >= total_length:
                    shutil.move(temp_path, final_path)
                    print()
                    return True

                # Otherwise, loop again to request remaining bytes
                attempt = 0  # reset attempt after successful network pass

            except KeyboardInterrupt:
                print("\nDownload interrupted by user. Partial file kept for resume.")
                return False
            except requests.RequestException as e:
                attempt += 1
                wait = min(60, 2 ** min(attempt, 6))
                print(f"\nNetwork error: {e}. Retrying in {wait}s...")
                time.sleep(wait)
                continue
    finally:
        # Ensure newline for clean prompt after carriage returns
        print()

# Main program starts here
# allows the use of the above objects to be imported as a module
if __name__ == '__main__':
    try:
        args = parse_arguments()
        skip_downloaded = args.skip

        shows = Shows()
        print(f'Club TWIT URL: {shows.url} \nDestination: {shows.twitclubdestination} \nBlocksize: {shows.blocksize} \n')
        twitclubblocksize = shows.blocksize
        for show in shows.shows():
            filename = shows.filename
            outputFilename = shows.outputFilename
            downloadfilename = shows.downloadfilename
            data=Data()
            if not data.isfilename(outputFilename):
                if not pathlib.Path(outputFilename).exists():
                    print(f'title: {shows.title} {shows.pubDate}')
                    print(f'descrition: {shows.description}')

                    # Check if URL is available before attempting to download
                    if shows.url:
                        try:
                            # Convert urllength to int safely
                            urllength_int = int(shows.urllength) if shows.urllength.isdigit() else 0
                            print(f'url: {shows.url} length: {humanize_size(urllength_int)} type: {shows.urltype}')
                            print(outputFilename)

                            if not skip_downloaded:
                                # Use resumable downloader; writes to shows.downloadfilename temp path
                                success = download_with_resume(
                                    url=shows.url,
                                    temp_path=downloadfilename,
                                    final_path=outputFilename,
                                    blocksize=twitclubblocksize,
                                    total_length=shows.urllength
                                )
                                if success:
                                    data.addfilename(outputFilename)
                            else:
                                # Skipping download per flag; mark as recorded
                                data.addfilename(outputFilename)
                        except requests.RequestException as e:
                            print(f"Error downloading {shows.url}: {e}")
                    else:
                        print("No URL available for this show. Skipping download.")
                        data.addfilename(outputFilename)
    except KeyboardInterrupt:
        print("\nProgram interrupted by user. Exiting.")
        sys.exit(0)
