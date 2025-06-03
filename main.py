import argparse
import os
import pathlib
import shutil
import sys
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
                            request = requests.get(shows.url, stream=True)
                            requestSizeRead = 0

                            if not skip_downloaded:
                                try:
                                    with open('twitclubdownload', 'wb') as fd:
                                        for chunk in request.iter_content(chunk_size=twitclubblocksize):
                                            fd.write(chunk)
                                            requestSizeRead += len(chunk)
                                            # Calculate percentage safely
                                            percentage = (float(requestSizeRead) / float(urllength_int) * 100) if urllength_int > 0 else 0
                                            print(f'completed {humanize_size(requestSizeRead)} {percentage:3.2f}%                    ', end='\r',
                                                  flush=True)
                                        print()
                                    request.close()
                                    shutil.move('twitclubdownload', outputFilename)
                                    data.addfilename(outputFilename)
                                except KeyboardInterrupt:
                                    print("\nDownload interrupted by user. Cleaning up...")
                                    request.close()
                                    # Remove the partial download file if it exists
                                    if os.path.exists('twitclubdownload'):
                                        os.remove('twitclubdownload')
                                    print("Cleanup complete. Exiting.")
                                    sys.exit(0)
                            else:
                                data.addfilename(outputFilename)
                        except requests.RequestException as e:
                            print(f"Error downloading {shows.url}: {e}")
                    else:
                        print("No URL available for this show. Skipping download.")
                        data.addfilename(outputFilename)
    except KeyboardInterrupt:
        print("\nProgram interrupted by user. Exiting.")
        sys.exit(0)
