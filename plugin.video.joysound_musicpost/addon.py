#/usr/bin/python
# plugin.video.joysound_musicpost
# Author: YWJamesLin

import os
import sys
from datetime import datetime
import time
import math

import xbmcaddon
import xbmcplugin
import xbmcgui
import xbmcvfs

import re
import requests
import json

from bs4 import BeautifulSoup as BS
from urllib.parse import parse_qsl
import urllib3
import ssl

# Parse plugin metadata
__url__ = sys.argv[0]
__handle__ = int (sys.argv[1])

xbmcplugin.setContent (__handle__,'movies')

class CustomHttpAdapter (requests.adapters.HTTPAdapter):
    # "Transport adapter" that allows us to use custom ssl_context.

    def __init__(self, ssl_context=None, **kwargs):
        self.ssl_context = ssl_context
        super().__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = urllib3.poolmanager.PoolManager(
            num_pools=connections, maxsize=maxsize,
            block=block, ssl_context=self.ssl_context)

# Class to handle JOYSOUND login session
class Session () :
    endpointBase = 'https://musicpost.joysound.com'

    thisAddon = None
    headers = None
    sessionAgent = None
    __language__ = None
    isLogin = False

    def __init__(self) :
        self.thisAddon = xbmcaddon.Addon ()
        self.__language__ = self.thisAddon.getLocalizedString

        self.headers = {
            'user-agent' : 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'origin' : self.endpointBase
        }

        # Create cookie storage directory
        self.storageDir = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))
        if not os.path.isdir (self.storageDir) :
            os.makedirs (self.storageDir)
        self.sessionAgent = requests.session ()
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ctx.options |= 0x4  # OP_LEGACY_SERVER_CONNECT
        self.sessionAgent = requests.session()
        self.sessionAgent.mount('https://', CustomHttpAdapter(ctx))
        if os.path.isfile (self.storageDir + '/cookie') :
            with open (self.storageDir + '/cookie', 'r') as handle :
                # Fetch saved session info
                content = handle.read()
                cookies = requests.utils.cookiejar_from_dict (json.loads (content))
                self.sessionAgent.cookies = cookies
                handle.close ()

    def checkIsLogin (self):
        result = self.sessionAgent.get (self.endpointBase + '/loginForm/sessionTimeOutFlg:false', headers = self.headers, allow_redirects = False)
        return result.status_code == 302

    # show main menu
    def mainMenu (self) :
        menuItems = []

        item = xbmcgui.ListItem (label = self.__language__ (33004))
        url = '{0}?action=search_target'.format (__url__)
        menuItems.append ((url, item, True))

        if self.isLogin :
            item = xbmcgui.ListItem (label = self.__language__ (33002))
            url = '{0}?action=favorite&page=1'.format (__url__)
            menuItems.append ((url, item, True))

            item = xbmcgui.ListItem (label = self.__language__ (33003))
            url = '{0}?action=logout'.format (__url__)
            menuItems.append ((url, item, True))
        else :
            item = xbmcgui.ListItem (label = self.__language__ (33005))
            url = '{0}?action=login'.format (__url__)
            menuItems.append ((url, item, True))

        xbmcplugin.addDirectoryItems (__handle__, menuItems, len (menuItems))
        xbmcplugin.endOfDirectory (__handle__)

    def searchTarget (self) :
        result = self.sessionAgent.get (self.endpointBase + '/musicList/page:1?target=7&method=2&keyword=test', headers = self.headers)
        soup = BS (result.content, 'html.parser')
        targetSelect = soup.find ('select', {'id' : 'target'})

        menuItems = []
        for targetItem in targetSelect.find_all ('option') :
            targetValue = targetItem['value']
            targetText = targetItem.text
            url = "{0}?action=search_method&target={1}".format (__url__, targetValue)
            menuItem = xbmcgui.ListItem (label = targetText)
            menuItems.append ((url, menuItem, True))

        xbmcplugin.addDirectoryItems (__handle__, menuItems, len (menuItems))
        xbmcplugin.endOfDirectory (__handle__)

    def searchMethod (self, target) :
        result = self.sessionAgent.get (self.endpointBase + '/musicList/page:1?target=7&method=2&keyword=test', headers = self.headers)
        soup = BS (result.content, 'html.parser')
        methodSelect = soup.find ('select', {'name' : 'method'})

        menuItems = []
        for methodItem in methodSelect.find_all ('option') :
            methodValue = methodItem['value']
            methodText = methodItem.text
            url = "{0}?action=search_songs&target={1}&method={2}".format (__url__, target, methodValue)
            menuItem = xbmcgui.ListItem (label = methodText)
            menuItems.append ((url, menuItem, True))

        xbmcplugin.addDirectoryItems (__handle__, menuItems, len (menuItems))
        xbmcplugin.endOfDirectory (__handle__)

    # search songs
    def searchSongs (self, target, method) :
        dialog = xbmcgui.Dialog ()
        keyword = dialog.input(self.__language__ (32014)) or ""
        del dialog
        if keyword is '':
            return
        result = self.sessionAgent.get (self.endpointBase + '/musicList/page:1', params = { 'target' : target, 'method' : method, 'keyword' : keyword }, headers = self.headers)
        soup = BS (result.content, 'html.parser')

        menuItems = self.createSongList (soup)

        xbmcplugin.addDirectoryItems (__handle__, menuItems, len (menuItems))
        xbmcplugin.addSortMethod (__handle__, xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.addSortMethod (__handle__, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
        xbmcplugin.endOfDirectory (__handle__)

    def searchResult (self, target, method, keyword, page) :
        result = self.sessionAgent.get (self.endpointBase + '/musicList/page:{0}'.format (page), params = { 'target' : target, 'method' : method, 'keyword' : keyword }, headers = self.headers)
        soup = BS (result.content, 'html.parser')

        menuItems = self.createSongList (soup)

        xbmcplugin.addDirectoryItems (__handle__, menuItems, len (menuItems))
        xbmcplugin.addSortMethod (__handle__, xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.addSortMethod (__handle__, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
        xbmcplugin.endOfDirectory (__handle__)


    # List favorite songs
    def favoriteSongs (self, page) :
        menuItems = []
        result = self.sessionAgent.get (self.endpointBase + '/musicList/page:{0}?favoriteMusic=on'.format (page), headers = self.headers)
        soup = BS (result.content, 'html.parser')

        menuItems = self.createSongList (soup)

        xbmcplugin.addDirectoryItems (__handle__, menuItems, len (menuItems))
        xbmcplugin.addSortMethod (__handle__, xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.addSortMethod (__handle__, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
        xbmcplugin.endOfDirectory (__handle__)

    def addToFavorite (self, sn) :
        self.sessionAgent.post (self.endpointBase + '/function/registerFavorite/musicId:{0}'.format(sn), [], headers = self.headers)

    def removeFromFavorite (self, sn) :
        self.sessionAgent.post (self.endpointBase + '/function/unenlistFavorite/musicId:{0}'.format(sn), [], headers = self.headers)

    # create video link and play on kodi
    def play (self, sn, name) :
        endpoint = self.parseSongVideoUrl(sn)
        if endpoint == False:
            dialog = xbmcgui.Dialog ()
            dialog.ok (self.__language__ (31001), self.__language__ (33013))
            return False
        thisSong = xbmcgui.ListItem (label = name)
        thisSong.setInfo ('video', {'title': name, 'genre': 'Music Video'})
        xbmc.Player ().play (endpoint , thisSong)

    def queue (self, sn, name) :
        endpoint = self.parseSongVideoUrl(sn)
        if endpoint == False:
            dialog = xbmcgui.Dialog ()
            dialog.ok (self.__language__ (31001), self.__language__ (33013))
            return False
        thisSong = xbmcgui.ListItem (label = name)
        thisSong.setInfo ('video', {'title': name, 'genre': 'Music Video'})
        xbmc.PlayList(1).add (endpoint , thisSong)

    def parseSongVideoUrl (self, sn) :
        result = self.sessionAgent.get (self.endpointBase + '/music/musicId:' + sn, headers = self.headers)
        soup = BS (result.content, 'html.parser')
        video = soup.find ('video', {'id':'video'})
        if video is None:
            return False
        return re.sub (r"\?pt=.*", "", video['src'])

    def createSongList (self, soup) :
        menuItems = []

        for songItem in soup.find_all ('div', {'class': 'music_block'}) :
            linkItem = songItem.find ('a', { 'class' : 'music' })
            imageBlock = songItem.find ('div', { 'class' : 'music_thumbnil' })
            titleBlock = songItem.find ('span', { 'class' : 'music_name' })
            artistBlock = songItem.find ('span', { 'class' : 'artist_name' })

            if titleBlock is None:
                continue
            title = titleBlock.text
            artist = artistBlock.text
            imageLink = imageBlock.img['src']
            sn = re.sub (r"/.+musicId:", "", linkItem['href'])
            menuItem = xbmcgui.ListItem (label = title + '/' + artist)
            menuItem.setArt ({'thumb': imageLink})
            url = "{0}?action=play&sn={1}&name={2}".format (__url__, sn, title + '/' + artist)
            queueUrl = "{0}?action=queue&sn={1}&name={2}".format (__url__, sn, title + '/' + artist)
            options = [(self.__language__ (30003), 'RunPlugin({0})'.format(queueUrl))]
            if self.isLogin :
                addToFavoriteUrl = "{0}?action=add_to_favorite&sn={1}".format (__url__, sn)
                removeFavoriteUrl = "{0}?action=remove_from_favorite&sn={1}".format (__url__, sn)
                options.append ((self.__language__ (30001), 'RunPlugin({0})'.format(addToFavoriteUrl)))
                options.append ((self.__language__ (30002), 'RunPlugin({0})'.format(removeFavoriteUrl)))
            menuItem.addContextMenuItems(options)
            menuItems.append ((url, menuItem, True))

        return menuItems

    # Login
    def login (self) :
        username = self.thisAddon.getSetting ('username')
        password = self.thisAddon.getSetting ('password')

        if username == '' or password == '':
            dialog = xbmcgui.Dialog ()
            dialog.ok (self.__language__ (31001), self.__language__ (32002))
            return False

        # combine login identity and CSRFToken to on-post data
        data = {
            'loginId' : username,
            'password' : password,
            'autoLoginFlg' : '1',
        }

        # Post Data and save session
        self.sessionAgent.post (self.endpointBase + '/login', data, headers = self.headers)
        with open (self.storageDir + '/cookie', 'w') as handle:
            cookieContent = json.dumps (requests.utils.dict_from_cookiejar (self.sessionAgent.cookies))
            handle.write (cookieContent)
            handle.close ()
        xbmc.executebuiltin('Container.Refresh')

    def logout (self) :
        dialog = xbmcgui.Dialog ()
        if dialog.yesno (self.__language__ (33003), self.__language__ (33012)) :
            os.remove (self.storageDir + '/cookie')
        xbmc.executebuiltin('Container.Refresh')

def router (paramString, session):
    session.isLogin = session.checkIsLogin()

    params = dict (parse_qsl (paramString[1:]))
    # Check Action
    if params :
        action = params['action']
        if action == 'favorite' :
            session.favoriteSongs (params ['page'])
        elif action == 'search_target' :
            session.searchTarget ()
        elif action == 'search_method' :
            session.searchMethod (params ['target'])
        elif action == 'search_songs' :
            session.searchSongs (params ['target'], params ['method'])
        elif action == 'search_result' :
            session.searchResult (params ['target'], params ['method'], params ['keyword'], params ['page'])
        elif action == 'add_to_favorite' :
            session.addToFavorite (params['sn'])
        elif action == 'remove_from_favorite' :
            session.removeFromFavorite (params['sn'])
        elif action == 'play' :
            session.play (params['sn'], params['name'])
        elif action == 'queue' :
            session.queue (params['sn'], params['name'])
        elif action == 'login' :
            session.login ()
        elif action == 'logout' :
            session.logout ()
    else :
        session.mainMenu ()

## Main
session = Session ()

if __name__ == '__main__' :
    router (sys.argv[2], session)
