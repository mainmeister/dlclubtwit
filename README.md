# **dlclubtwit**

Download videos from a club twit subscription to watch them using kodi.

# **Installation**

There are three environment variables that the program depends on.

`# set up configuration for the twit club downloader`

`# twitcluburl - the url from the twit club for your shows`

`export twitcluburl=https://twit.memberfulcontent.com/rss/9041?auth={your authorization here}`

`# twitclubblocksize - the size of the block to read from the stream while downloading`

`export twitclubblocksize=1048576`

`# twitclubdestination - the location for the downloaded files`

`export twitclubdestination=/home/mainmeister/kodi/kodi/twit.tv`

The twitcluburl is the one you get from the club twit subscriber's Podcast page. This is a manditory setting. If this is missing then the program will abort with an appropriate error message "Set environment string twitcluburl to the url for your twitclub stream" and an exit code of 1.

The twitclubblocksize sets the size of each data block requested from the server. The larger the size the more efficient. If this is not set then the program defaults to 1 megabyte blocks.

The twitclubdestination is the path on your file system where you want to put the downloaded files. If this is not set then the current working directory is used.

# **Requirements**

Python3.6+

`sudo apt install python`

requests

`$ python -m pip install requests`

html2txt

`git clone https://github.com/renesugar/html2txt.git`

python-dotenv (for testing with .env file)

`$ python -m pip install python-dotenv`

Alternatively, you can install all dependencies using the requirements.txt file:

`$ python -m pip install -r requirements.txt`

# **Usage**

The program is a command line python script. There are no command line arguments.

`$python main.py`

# **Testing**

For testing purposes, you can use a `.env` file to set environment variables instead of exporting them in your shell. This is especially useful for running tests without affecting your system environment.

Create a `.env` file in the project root with the following content:

```
# Required: URL from the TWIT club for your shows
twitcluburl=https://twit.memberfulcontent.com/rss/9041?auth=your_auth_token_here

# Optional: Block size for downloading (default: 1048576)
twitclubblocksize=1048576

# Optional: Destination folder for downloads (default: current directory)
twitclubdestination=./downloads
```

To use the `.env` file in your tests, use the `python-dotenv` package:

```python
import dotenv
dotenv.load_dotenv()
```

See `test_shows.py` for an example of how to use the `.env` file in tests.

# **Output**

(venv) mainmeister@william-optiplex7020:~/PycharmProjects/dltwit$ python main.py
title: This Week in Google 609 Put Garlic On My Shopping List Wed, 28 Apr 2021 22:02:33 PDT
descrition: * Google Earnings Smash Sales Records as Digital Ad Market Booms
* Amazon, Apple, Facebook, and Google became big tech companies by acquiring hundreds of smaller companies
* Google Cloud brings in $4B in Q1, up 46 percent
* Google Fiber coming to another Utah city
* Sundar Pichai talks about COVID in India
* Google's Oscar commercial
* Apple reports another blowout quarter with sales up 54%, authorizes $90 billion in share buybacks
* Dogecoin price surges after tweets from Elon Musk and Mark Cuban
* Amazon to hike wages for over 500,000 workers
* 4chan founder Chris Poole has left Google
* What really happened at Basecamp
* YouTube is a media juggernaut that could soon equal Netflix in revenue
* Roku says it may lose YouTube TV app after Google made anti-competitive demands
* Comic unapologetic about putting garlic on fans shopping lists
* Google adds COVID restriction alerts, new road-trip mapping features, as vaccines enable safer travel
* Google Fi marks 6th birthday with new 'Simply Unlimited' plan that lacks 'Unlimited Plus' extras
* Google-run Android Earthquake Alerts System is now providing warnings in first two countries
* Google Assistant can now correctly set timers or alarms even after you flub a voice command
* Google Photos for Android rolling out new 'Sharpen' and 'Denoise' editor tools
* Google Assistant can now correctly set timers or alarms even after you flub a voice command
* YouTube adds even more video resolution controls and options on mobile
* It took Google 526 days to give you a way to search through Stadia's 172 games
* Kevin Tofel: Looks like I'm going to be a GT Yellow Jacket
* What Old Tiktok-ERs Look like (by Ant)
* Be Mindful Of The Dance Moves You're Doing On Tiktok
* Pichai teases 'significant' announcements at Google I/O 2021 as product cycles return to normal
* Google posts I/O 2021 schedule, starting with Sundar Pichai keynote on May 18 at 10 a.m
* Samsung unpacks its Galaxy Book Pro, Pro 360 and more
* Amazon sees 'positive outcome' in FCC's SpaceX satellite ruling
* Minutes before Trump left office, millions of the Pentagon's dormant IP addresses sprang to life
* Daniel Kaminsky, Internet Security Savior, Dies at 42
* Introducing Immersive View, A Fun New Way to Meet
* 90s Kids Guide to the Internet
* WaPo reports on brain interfaces with a touch of moral panic
* She never returned a VHS of Sabrina and 20 years later faced a felony
* Verizon Explores Sale of Media Assets, Including Parts of Yahoo and AOL
Picks:

* Stacey - Ember Mug
* Jeff - Oscar Viewership Rises To 10.4M In Final Numbers
* Ant - I Finally Created an NFT (Why not?)
* Ant - My Newest Short Film
* Ant - Photo Pursuit: Stories Behind the Photographs

**Hosts:** [Leo Laporte](https://twit.tv/people/leo-laporte), [Stacey Higginbotham](https://twit.tv/people/stacey-higginbotham), [Jeff Jarvis](https://twit.tv/people/jeff-jarvis), and [Ant Pruitt](https://twit.tv/people/ant-pruitt) 



url: https://cdn.twit.tv/members/twig/twig_609/twig_609_h264m_825983-4ced8549.mp4 length: 2147483647 type: video/mp4
/home/mainmeister/kodi/kodi/twit.tv/This Week in Google 609 Put Garlic On My Shopping List.mp4
completed 116.97%
title: Hands-On Tech Mach-E One Month Review Wed, 28 Apr 2021 18:30:09 PDT
descrition: Leo Laporte gives his one-month review of Ford's all-electric SUV, the Mustang Mach-E.

**Host:** [Leo Laporte](https://twit.tv/people/leo-laporte) 

Find more products we recommend at[https://www.amazon.com/shop/twitnetcastnetwork](https://www.amazon.com/shop/twitnetcastnetwork)


url: https://cdn.twit.tv/members/hot/hot_139/hot_139_h264m_825977-1cc97039.mp4 length: 1157155358 type: video/mp4
/home/mainmeister/kodi/kodi/twit.tv/Hands-On Tech Mach-E One Month Review.mp4
completed 100.00%
title: Windows Weekly 722 Everyone's Drinkin' at Home Wed, 28 Apr 2021 16:26:04 PDT
descrition: MSFT Q3 FY21 earnings

* Paul Thurrott's Short Takes: Microsoft Earnings Special Edition
* Microsoft Posts Huge Numbers in Latest Quarter
* Microsoft says Windows 10 now on 1.3 billion monthly active devices
* Microsoft: Teams is now at 145 million daily active users
* Sony Has Sold Almost 8 Million PlayStation 5 Consoles
* Microsoft: LinkedIn topped $3 billion in ad revenue in last year, outpacing Snap and Pinterest
* Spotify Now Has 356 Million Users
* Intel Reports Flat Revenues Despite PC Boom
* AMD's Datacenter Revenues More Than Doubled in Quarter
* Alphabet Announces Quarterly Results


Fun 

* Microsoft Wants a New Font
* MyBuild
* Yusuf Mehdi | Twitter


Windows 10 

* Windows 10 Version 20H2 Hits 40 Percent Usage Share
* Releasing Windows Feature Experience Pack 120.2212.3740.0 to the Beta &amp; Release Preview Channels
* Microsoft to bring News and Interests feature to Windows 10 users running 1909 and above


Microsoft 365 

* Microsoft makes previews available of its non-subscription Office products
* Amazon Announces New Fire HD 10 Tablets
* Viva Learning Enters Public Preview
* Microsoft Classroom Pen 2 Arrives Next Week


Tips and picks 

* Tip of the week: Games with Gold
* App pick of the week: Xbox Cloud Gaming Beta
* Enterprise pick of the week: Cheat sheet: How to join Teams meetings from work conference rooms
* Codename pick of the week: Alexandria
* Beer pick of the week: Evil Twin Stay Home (version 3, the Royal Treatment)

**Hosts:** [Leo Laporte](https://twit.tv/people/leo-laporte), [Mary Jo Foley](https://twit.tv/people/mary-jo-foley), and [Paul Thurrott](https://twit.tv/people/paul-thurrott) 

Check out Paul's blog at[thurrott.com](https://www.thurrott.com/) 

Check out Mary Jo's blog at[AllAboutMicrosoft.com](http://allaboutmicrosoft.com/) 

The Windows Weekly theme music is courtesy of[Carl Franklin](https://twitter.com/carlfranklin).


url: https://cdn.twit.tv/members/ww/ww_722/ww_722_h264m_825967-ae7d993a.mp4 length: 1519581806 type: video/mp4
/home/mainmeister/kodi/kodi/twit.tv/Windows Weekly 722 Everyone's Drinkin' at Home.mp4
completed 100.00%
