# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of Sick Beard.
#
# Sick Beard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Sick Beard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

import urllib
import re
from xml.dom.minidom import parseString

import sickbeard
import generic

from sickbeard.common import Quality
from sickbeard import logger
from sickbeard import tvcache
from sickbeard.helpers import sanitizeSceneName, get_xml_text
from sickbeard.exceptions import ex

class KATProvider(generic.TorrentProvider):

    def __init__(self):

        generic.TorrentProvider.__init__(self, "KAT")
        
        self.supportsBacklog = True

        self.cache = KATCache(self)

        self.url = 'http://kat.ph/'

    def isEnabled(self):
        return sickbeard.KAT
        
    def imageName(self):
        return 'kat.png'
      
    def getQuality(self, item):
        
        #torrent_node = item.getElementsByTagName('torrent')[0]
        #filename_node = torrent_node.getElementsByTagName('title')[0]
        #filename = get_xml_text(filename_node)
        
        # I think the only place we can get anything resembing the filename is in 
        # the title
        filename = get_xml_text(item.getElementsByTagName('title')[0])

        quality = Quality.nameQuality(filename)
        
        return quality

    def findSeasonResults(self, show, season):
        
        results = {}
        
        if show.air_by_date:
            logger.log(u"KAT doesn't support air-by-date backlog because of limitations on their RSS search.", logger.WARNING)
            return results
        
        results = generic.TorrentProvider.findSeasonResults(self, show, season)
        
        return results
    def _get_season_search_strings(self, show, season=None):
    
        params = {}
    
        if not show:
            return params
        
        params['show_name'] = sanitizeSceneName(show.name).replace('.',' ').encode('utf-8')
          
        if season != None:
            params['season'] = season
    
        return [params]

    def _get_episode_search_strings(self, ep_obj):
    
        params = {}
        
        if not ep_obj:
            return params
                   
        params['show_name'] = sanitizeSceneName(ep_obj.show.name).replace('.',' ').encode('utf-8')
        
        if ep_obj.show.air_by_date:
            params['date'] = str(ep_obj.airdate)
        else:
            params['season'] = ep_obj.season
            params['episode'] = ep_obj.episode
            
        logger.log(u"KAT _get_episode_search_strings for %s is returning %s" % (repr(ep_obj), repr(params)), logger.DEBUG)
    
        return [params]

    def _doSearch(self, search_params, show=None):
    
        params = {"rss": "1"}
    
        if search_params:
            params.update(search_params)
            
        # http://kat.ph/usearch/%22james%20may%22%20verified:1%20season:1%20episode:1/?rss=1
        
        searchURL = self.url + 'usearch/' 
        
        # Many of the 'params' here actually belong in the path as name:value pairs.
        # so we remove the ones we know about (adding them to the path as we do so)
        if 'show_name' in params:
            searchURL = searchURL + urllib.quote('"' + params.pop('show_name') + '"') +"%20"
      
        if 'season' in params:
            searchURL = searchURL + 'season:' + str(params.pop('season')) +"%20"
            
        if 'episode' in params:
            searchURL = searchURL + 'episode:' + str(params.pop('episode')) +"%20"
            
        if 'date' in params:
            logger.log(u"Sorry, air by date not supported by kat.  Removing: " + params.pop('date'), logger.WARNING)
            
            
        # we probably have an extra %20 at the end of the url.  Not likely to 
        # cause problems, but it is uneeded, so trim it
        if searchURL.endswith('%20'):
            searchURL = searchURL[:-3]
        
        
        searchURL = searchURL + '/?' + urllib.urlencode(params) # this will likely only append the rss=1 part

        logger.log(u"Search string: " + searchURL, logger.DEBUG)

        data = self.getURL(searchURL)

        if not data:
            return []
        
        try:
            parsedXML = parseString(data)
            items = parsedXML.getElementsByTagName('item')
        except Exception, e:
            logger.log(u"Error trying to load KAT RSS feed: "+ex(e), logger.ERROR)
            logger.log(u"RSS data: "+data, logger.DEBUG)
            return []
        
        results = []

        for curItem in items:
            
            (title, url) = self._get_title_and_url(curItem)
            
            if not title or not url:
                logger.log(u"The XML returned from the KAT RSS feed is incomplete, this result is unusable: "+data, logger.ERROR)
                continue
    
            results.append(curItem)

        return results

    def _get_title_and_url(self, item):
        #(title, url) = generic.TorrentProvider._get_title_and_url(self, item)

        title = get_xml_text(item.getElementsByTagName('title')[0])
        url = item.getElementsByTagName('enclosure')[0].getAttribute('url').replace('&amp;','&')

        return (title, url)

    def _extract_name_from_filename(self, filename):
        name_regex = '(.*?)\.?(\[.*]|\d+\.TPB)\.torrent$'
        logger.log(u"Comparing "+name_regex+" against "+filename, logger.DEBUG)
        match = re.match(name_regex, filename, re.I)
        if match:
            return match.group(1)
        return None
    
#    <item>
#        <title>James Mays Things You Need To Know S02E06 HDTV XviD-AFG</title>
#        <description>random text in here</description>        
#        <category>Tv</category>
#        <link>http://kat.ph/james-mays-things-you-need-to-know-s02e06-hdtv-xvid-afg-t6666685.html</link>
#        <guid>http://kat.ph/james-mays-things-you-need-to-know-s02e06-hdtv-xvid-afg-t6666685.html</guid>
#        <pubDate>Mon, 17 Sep 2012 22:48:02 +0000</pubDate>
#        <torrentLink>http://kat.ph/james-mays-things-you-need-to-know-s02e06-hdtv-xvid-afg-t6666685.html</torrentLink>
#        <hash>556022412DE29EE0B0AC1ED83EF610AA3081CDA4</hash>
#        <peers>0</peers>
#        <seeds>0</seeds>
#        <leechs>0</leechs>
#        <size>255009149</size>
#        <verified>1</verified>
#        <enclosure url="https://torcache.net/torrent/556022412DE29EE0B0AC1ED83EF610AA3081CDA4.torrent?title=[kat.ph]james.mays.things.you.need.to.know.s02e06.hdtv.xvid.afg" length="255009149" type="application/x-bittorrent" />
#    </item>


class KATCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll KAT every 15 minutes max
        self.minTime = 15


    def _getRSSData(self):
        url = self.provider.url + 'tv/?rss=1'

        logger.log(u"KAT cache update URL: "+ url, logger.DEBUG)

        data = self.provider.getURL(url)

        return data

    def _parseItem(self, item):

        (title, url) = self.provider._get_title_and_url(item)

        if not title or not url:
            logger.log(u"The XML returned from the KAT RSS feed is incomplete, this result is unusable", logger.ERROR)
            return

        logger.log(u"Adding item from RSS to cache: "+title, logger.DEBUG)

        self._addCacheEntry(title, url)

provider = KATProvider()