import argparse
import os
import pathlib
import shutil
import xml.etree.ElementTree as ET
import sqlite3
import requests
import time
import re # Added for cleanTitle
import sys # For sys.exit
import traceback # For traceback.print_exc
from requests.exceptions import RequestException
from html2txt import converters

# Define custom exceptions
class MissingConfigurationError(Exception):
    pass

class XMLParsingError(Exception):
    pass

class DatabaseError(sqlite3.Error): # Inherit from sqlite3.Error for specificity
    pass

# Helper function for robust requests.get
def requests_get_with_retry(url, max_retries=3, backoff_factor=0.5, **kwargs):
    for attempt_num in range(max_retries):
        try:
            response = requests.get(url, **kwargs)
            response.raise_for_status()  # Raise an exception for bad status codes
            return response
        except RequestException as e:
            error_type = type(e).__name__
            error_message = str(e)
            delay = backoff_factor * (2 ** attempt_num)
            print(f"Network error ([{attempt_num + 1}]/[{max_retries}]): {error_type} - {error_message}. Retrying in {delay:.2f}s...")
            if attempt_num == max_retries - 1:
                print("Max retries reached. Failing.")
                raise
            time.sleep(delay)
    # This line should ideally not be reached if max_retries > 0
    raise RequestException(f"Failed to fetch {url} after {max_retries} retries.")


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
    def __init__(self):
        sql_create = """
        create table if not exists file (filename text unique);
        """
        try:
            self.data = sqlite3.connect('dltwit.sqlite')
            self.data.executescript(sql_create)
        except sqlite3.Error as e:
            print(f"Error connecting to or initializing database: {e}")
            raise DatabaseError(f"Database connection/initialization failed: {e}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.data:
            self.data.close()
            print("Database connection closed.")

    # check if filename exists in the filename table
    # return true if it does
    def isfilename(self, filename):
        sql_select = """
        select count(*) from file where filename=?
        """
        try:
            row = self.data.execute(sql_select, (filename,))
            result = row.fetchone()
            if result is None: # Should not happen with count(*) but good practice
                return False
            return result[0] > 0
        except sqlite3.Error as e:
            print(f"Database error in isfilename: {e}")
            raise DatabaseError(f"isfilename failed: {e}")

    # Add a new filename to the filename table
    def addfilename(self, filename):
        sql_insert ="""
insert into file (filename)
values (?);        """
        try:
            self.data.execute(sql_insert, (filename,))
            self.data.commit()
        except sqlite3.Error as e:
            print(f"Database error in addfilename: {e}")
            raise DatabaseError(f"addfilename failed: {e}")

    # Delete a filename from the filename table
    # Not currently used. A future command line option
    # will use this to allow the removal of a name
    def delfilename(self, filename):
        sql_delete = """
        delete from file where filename=?
        """
        try:
            self.data.execute(sql_delete, (filename,))
            self.data.commit()
        except sqlite3.Error as e:
            print(f"Database error in delfilename: {e}")
            raise DatabaseError(f"delfilename failed: {e}")

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
            print('Error: The environment variable twitcluburl must be set to the URL of your TWiT Club RSS feed.')
            raise MissingConfigurationError("twitcluburl environment variable not set.")

        try:
            self.blocksize = int(os.environ.get('twitclubblocksize', 1048576))
        except ValueError:
            print("Warning: twitclubblocksize environment variable is not a valid integer. Using default value 1048576.")
            self.blocksize = 1048576
        
        destination_path_str = os.environ.get('twitclubdestination', './')
        self.twitclubdestination = os.path.abspath(destination_path_str)

        if os.path.exists(self.twitclubdestination):
            if not os.path.isdir(self.twitclubdestination):
                raise NotADirectoryError(f"twitclubdestination path exists but is not a directory: {self.twitclubdestination}")
        else:
            try:
                os.makedirs(self.twitclubdestination, exist_ok=True)
            except OSError as e:
                raise IOError(f"Could not create twitclubdestination directory: {self.twitclubdestination}. Error: {e}")

        # Request the xml feed and parse it
        try:
            r = requests_get_with_retry(self.url, max_retries=3, backoff_factor=0.5)
            self.root = ET.fromstring(r.text)
        except ET.ParseError as e:
            error_msg = f"Failed to parse XML feed: {e}"
            print(f"Critical: {error_msg}")
            raise XMLParsingError(error_msg)
        except RequestException as e:
            print(f"Critical: Could not fetch TWiT Club XML feed from {self.url} after multiple retries. Error: {e}")
            raise # Re-raise the exception to halt execution if XML feed cannot be obtained.

    # Objectify the XML structure
    def shows(self):
        if self.root is None: # Should not happen if __init__ succeeded, but as a safeguard
            return

        for show_item in self.root.iter('item'):
            title_element = show_item.find('title')
            if title_element is None or title_element.text is None:
                print("Warning: Skipping show due to missing 'title' in XML item.")
                continue
            current_title = self.cleanTitle(title_element.text)

            enclosure_element = show_item.find('enclosure')
            if enclosure_element is None:
                print(f"Warning: Skipping show '{current_title}' due to missing 'enclosure' information in XML item.")
                continue

            try:
                self.url = enclosure_element.attrib['url']
                self.urllength = enclosure_element.attrib['length'] # type is optional
            except KeyError as e:
                print(f"Warning: Skipping show '{current_title}' because 'enclosure' tag is missing attribute: {e}.")
                continue
            
            self.urltype = enclosure_element.attrib.get('type', 'audio/mpeg') # Default if not present

            description_element = show_item.find('description')
            if description_element is None or description_element.text is None:
                self.description = "No description available"
            else:
                self.description = converters.Html2Markdown().convert(description_element.text)

            pubDate_element = show_item.find('pubDate')
            if pubDate_element is None or pubDate_element.text is None:
                self.pubDate = "Unknown publication date"
            else:
                self.pubDate = pubDate_element.text
            
            # Assign other instance variables needed for download
            self.title = current_title 
            # self.enclosure is not strictly needed as an instance var if its parts are extracted
            self.filename = self.title + '.mp4' # Assuming all are mp4, or derive from urltype
            self.outputFilename = os.path.join(self.twitclubdestination, self.filename)
            self.downloadfilename = os.path.join(self.twitclubdestination, 'twitclubdownload')
            
            yield show_item # Yield the original item, or a dict of processed values

    # Clean up the title of the show by removing bad characters
    def cleanTitle(self, title):
        newTitle = str(title)

        # Replace a comprehensive set of problematic characters with underscores
        # Includes: Windows disallowed, control characters, and other script/path problematic chars
        # Note: \x00-\x1F covers ASCII control characters.
        # The literal backslash \ is escaped as \\ in the regex.
        newTitle = re.sub(r'[<>:"/\\|?*\x00-\x1F!$\'@&#%;(){}\[\]]', '_', newTitle)

        # Replace multiple consecutive underscores with a single underscore
        newTitle = re.sub(r'_+', '_', newTitle)

        # Remove leading and trailing spaces, dots, and underscores
        newTitle = newTitle.strip(' ._')

        # If the title becomes empty after cleaning, provide a default name
        if not newTitle:
            newTitle = "untitled_show"
            
        # Length limitation is deferred as per instructions.
        # Handling reserved filenames (CON, PRN, etc.) is also deferred.

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
    args = parse_arguments()
    try:
        skip_downloaded = args.skip

        shows = Shows()
        print(f'Club TWIT URL: {shows.url} \nDestination: {shows.twitclubdestination} \nBlocksize: {shows.blocksize} \n')
        twitclubblocksize = shows.blocksize
        for show_item_xml in shows.shows(): # Renamed to avoid confusion with the shows object
            # Properties like shows.title, shows.url etc. are set by the shows.shows() generator
            filename = shows.filename
            outputFilename = shows.outputFilename
            downloadfilename = shows.downloadfilename # This is shows.twitclubdestination + 'twitclubdownload'

            try:
                with Data() as data:
                    if not data.isfilename(outputFilename):
                        if not pathlib.Path(outputFilename).exists():
                            print(f'title: {shows.title} {shows.pubDate}')
                            print(f'descrition: {shows.description}')
                            print(f'url: {shows.url} length: {humanize_size(int(shows.urllength))} type: {shows.urltype}')
                            print(outputFilename)

                            request = None # Ensure request is defined for finally block
                            try:
                                request = requests_get_with_retry(shows.url, max_retries=3, backoff_factor=0.5, stream=True)
                            except RequestException as e:
                                print(f"Failed to download {shows.title} from {shows.url} after multiple retries. Error: {e}")
                                continue # Skip to the next show

                            download_successful = False
                            temp_file_opened_and_written = False
                            try: # This try encompasses file open, download, and move
                                temp_file_opened_and_written = False # Initialize before open attempt
                                download_io_error = False
                                try:
                                    # Attempt to open the temporary file
                                    with open(downloadfilename, 'wb') as fd:
                                        requestSizeRead = 0
                                        try: # Inner try for the download writing loop
                                            for chunk in request.iter_content(chunk_size=twitclubblocksize):
                                                fd.write(chunk)
                                                requestSizeRead += len(chunk)
                                                # Progress display
                                                print(f'completed {humanize_size(requestSizeRead)} {(float(requestSizeRead) / float(shows.urllength) * 100):3.2f}%                    ', end='\r', flush=True)
                                            print() # Clear progress line after successful loop
                                            temp_file_opened_and_written = True # Mark file as successfully written
                                        except IOError as e: # Error during fd.write(chunk)
                                            print() # Clear progress line
                                            print(f"Error writing download stream for '{shows.title}' to {downloadfilename}: {e}")
                                            download_io_error = True # Signal that writing failed
                                        # No specific handling for requests.exceptions.ChunkedEncodingError here,
                                        # as iter_content might raise it, but it's often a server issue.
                                        # requests_get_with_retry should handle persistent request issues.

                                except IOError as e: # Error opening the temporary file
                                    print(f"Failed to open temporary download file {downloadfilename} for '{shows.title}': {e}")
                                    # Ensure request is closed if open fails, then skip this show
                                    if request:
                                        request.close()
                                    continue # Skip to the next show
                                
                                if download_io_error: # If writing to disk failed
                                    # Request is closed in finally, temp file (if partially created) cleaned up in finally
                                    continue # Skip to the next show

                                # If file was opened and written to successfully, attempt to move
                                if temp_file_opened_and_written:
                                    try:
                                        shutil.move(downloadfilename, outputFilename)
                                        print(f"Successfully downloaded and saved: {outputFilename}")
                                        download_successful = True
                                    except (shutil.Error, OSError) as e:
                                        print() # Ensure newline
                                        print(f"Failed to move downloaded file for '{shows.title}' from {downloadfilename} to {outputFilename}: {e}")
                                        # download_successful remains False, temp file will be cleaned up by finally
                                # else: download was not successful or file not written, skip adding to DB
                            
                            finally:
                                if request:
                                    request.close()
                                # Cleanup temporary file if it was (potentially partially) written and still exists
                                # temp_file_opened_and_written ensures we only try to delete if writing finished.
                                # If open failed, or write failed mid-way, downloadfilename might exist or not.
                                # os.path.exists is the key check.
                                if os.path.exists(downloadfilename): # Check if temp file exists before trying to remove
                                    try:
                                        os.remove(downloadfilename)
                                        # Only print removal message if it was supposed to be a full file that failed to move,
                                        # or if it was a partial that we are cleaning.
                                        if temp_file_opened_and_written and not download_successful: # It was written but not moved
                                            print(f"Temporary file {downloadfilename} (completed download, failed move) removed.")
                                        elif download_io_error: # It was partially written
                                             print(f"Partial temporary file {downloadfilename} removed.")
                                        # else: if open failed, no message needed here.
                                    except OSError as e:
                                        print(f"Warning: Failed to remove temporary download file {downloadfilename}: {e}")
                            
                            if download_successful:
                                data.addfilename(outputFilename)
                            
                        else: # pathlib.Path(outputFilename).exists() is true
                            # Ensure progress line is cleared if previous operation used `end='\r'`
                            # However, the prints for existing files are already on new lines.
                            print(f"File {outputFilename} already exists. Skipping download, adding to DB if not present.")
                            if not data.isfilename(outputFilename): # Add to DB if it exists but not tracked
                                 data.addfilename(outputFilename)
                    else: # data.isfilename(outputFilename) is true
                        print(f"File {outputFilename} already recorded as downloaded. Skipping.")
                
                    # Handling for skip_downloaded argument (which means skip the actual download bytes part)
                    if skip_downloaded and not data.isfilename(outputFilename) and pathlib.Path(outputFilename).exists():
                        print(f"Skipping download for existing file as per --skip: {outputFilename}. Marking as downloaded.")
                        data.addfilename(outputFilename)

            except DatabaseError as e:
                print(f"A database error occurred: {e}. Skipping processing for show: {shows.title if hasattr(shows, 'title') else 'Unknown'}")
                # Depending on severity, might want to break or sys.exit
                continue # Continue to next show
            except Exception as e: # Catch any other unexpected error for this show item
                print(f"An unexpected error occurred processing show {shows.title if hasattr(shows, 'title') else 'Unknown'}: {e}")
                continue
    except MissingConfigurationError as e: # Specific handling for this custom error if it's fatal
        print(f"Configuration Error: {e}", flush=True)
        sys.exit(1)
    except XMLParsingError as e: # Specific handling for this custom error if it's fatal
        print(f"XML Parsing Error: {e}", flush=True)
        # traceback.print_exc() # Optionally print traceback for XML errors too
        sys.exit(1)
    # Not catching DatabaseError at top level as it's handled per show, allowing script to continue.
    except Exception as e:
        print(f"\n--- An unexpected and unhandled error occurred ---", flush=True)
        print(f"Error Type: {type(e).__name__}", flush=True)
        print(f"Error Message: {e}", flush=True)
        print(f"--- Traceback ---", flush=True)
        traceback.print_exc()
        sys.exit(1)
