import argparse
import os
import pathlib
import shutil
import xml.etree.ElementTree as ET
import sqlite3
import requests
from html2txt import converters

def parse_arguments():
    parser = argparse.ArgumentParser(description="Process command-line arguments.")
    parser.add_argument("-s", "--skip", action="store_true", help="Skip new episodes.")
    args = parser.parse_args()
    return args


class Data():


    def __init__(self):
        sql_create = """
        create table if not exists file (filename text unique);
        """
        self.data = sqlite3.connect('dltwit.sqlite')
        self.data.executescript(sql_create)

    def isfilename(self, filename):
        sql_select = """
        select count(*) from file where filename=?
        """
        row = self.data.execute(sql_select, (filename,))
        result = row.fetchone()
        return result[0] > 0

    def addfilename(self, filename):
        sql_insert ="""
insert into file (filename)
values (?);        """
        self.data.execute(sql_insert, (filename,))
        self.data.commit()

    def delfilename(self, filename):
        sql_delete = """
        delete from file where filename=?
        """
        self.data.execute(sql_delete, (filename,))
        self.data.commit()

class Shows():

    def __init__(self):
        try:
            self.url = os.environ['twitcluburl']
        except KeyError:
            print('Set environment string twitcluburl to the url for your twitclub stream')
            quit(1)
        try:
            self.blocksize = int(os.environ['twitclubblocksize'])
        except KeyError:
            self.blocksize = 1048576
        try:
            self.twitclubdestination = os.environ['twitclubdestination']
        except KeyError:
            self.twitclubdestination = os.path.abspath('./')
        r = requests.get(self.url)
        self.root = ET.fromstring(r.text)

    def shows(self):
        for show in self.root.iter('item'):
            self.description = converters.Html2Markdown().convert(show.find('description').text)
            self.title = self.cleanTitle(show.find('title').text)
            self.pubDate = show.find('pubDate').text
            self.enclosure = show.find('enclosure')
            self.url = shows.enclosure.attrib['url']
            self.urllength = shows.enclosure.attrib['length']
            self.urltype = shows.enclosure.attrib['type']
            self.filename = shows.title + '.mp4'
            self.outputFilename = os.path.join(shows.twitclubdestination, self.filename)
            self.downloadfilename = os.path.join(shows.twitclubdestination, 'twitclubdownload')
            yield show

    def cleanTitle(self, title):
        newTitle = str(title)
        badCharacters = '\\/:.+?*'
        for badCharacter in badCharacters:
            newTitle = newTitle.replace(badCharacter, '')
        return newTitle

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

if __name__ == '__main__':
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
                print(f'url: {shows.url} length: {humanize_size(int(shows.urllength))} type: {shows.urltype}')
                print(outputFilename)
                request = requests.get(shows.url, stream=True)
                requestSizeRead = 0
                if not skip_downloaded:
                    with open('twitclubdownload', 'wb') as fd:
                        for chunk in request.iter_content(chunk_size=twitclubblocksize):
                            fd.write(chunk)
                            requestSizeRead += len(chunk)
                            print(f'completed {humanize_size(requestSizeRead)} {(float(requestSizeRead) / float(shows.urllength) * 100):3.2f}%                    ', end='\r',
                                  flush=True)
                        print()
                    request.close()
                    shutil.move('twitclubdownload', outputFilename)
                data.addfilename(outputFilename)
