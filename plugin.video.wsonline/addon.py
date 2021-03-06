# -*- coding: utf-8 -*-
import os.path as path
import json
import re
import urllib
import ssl
import requests
import WebUtils
from xbmcswift2 import Plugin, xbmc, ListItem, download_page, clean_dict, SortMethod
ssl._create_default_https_context = ssl._create_unverified_context

plugin = Plugin()
__BASEURL__ = 'https://watchseries-online.pl'
__addondir__ = xbmc.translatePath(plugin.addon.getAddonInfo('path'))
__datadir__ = xbmc.translatePath('special://profile/addon_data/{0}/'.format(plugin.id))
__resdir__ = path.join(__addondir__, 'resources')
__imgsearch__ = path.join(__resdir__, 'search.png')
__savedjson__ = path.join(xbmc.translatePath(plugin.addon.getAddonInfo('profile')), 'savedshows.json')
getWeb = WebUtils.BaseRequest(path.join(__datadir__, 'cookies.lwp'))


@plugin.route('/')
def index():
    litems = []
    plugin.set_content('movies')
    itemsaved = {'label': 'Saved Shows', 'path': plugin.url_for(saved), 'icon': 'DefaultFolder.png', 'thumbnail': 'DefaultFolder.png'}
    itemplay = {'label': 'Resolve URL and Play (URLresolver required)', 'path': plugin.url_for(playurl), 'icon': 'DefaultFolder.png', 'thumbnail': 'DefaultFolder.png'}
    itemlatest = {'label': 'Last 350 Episodes', 'icon': 'DefaultFolder.png', 'thumbnail': 'DefaultFolder.png', 'path': plugin.url_for(latest)}
    itemsearch = {'label': 'Search', 'icon': __imgsearch__, 'thumbnail': __imgsearch__, 'path': plugin.url_for(search)}
    litems.append(itemlatest)
    litems.append(itemsearch)
    litems.append(itemsaved)
    litems.append(itemplay)
    return litems


def loadsaved():
    sitems = []
    litems = []
    items = []
    savedpath = ''
    try:
        savedpath = path.join(__datadir__, "saved.json")
        if path.exists(savedpath):
            fpin = file(savedpath)
            rawjson = fpin.read()
            sitems = json.loads(rawjson)
            fpin.close()
        else:
            return []
        for item in sitems:
            li = ListItem.from_dict(**item)
            litems.append(li)
    except:
        pass
    return litems


def makecatitem(name, link, removelink=False):
    item = {}
    ctxitem = {}
    itempath = plugin.url_for(category, name=name, url=link)
    item = {'label': name, 'label2': link, 'icon': 'DefaultFolder.png', 'thumbnail': 'DefaultFolder.png', 'path': itempath}
    item.setdefault(item.keys()[0])
    litem = ListItem.from_dict(**item)
    if removelink:
        litem.add_context_menu_items([('Remove Saved Show', 'RunPlugin("{0}")'.format(plugin.url_for(removeshow, name=name, link=link)),)])
    else:
        litem.add_context_menu_items([('Save Show', 'RunPlugin("{0}")'.format(plugin.url_for(saveshow, name=name, link=link)),)])
    return litem


@plugin.route('/playurl')
def playurl():
    url = ''
    url = plugin.keyboard(default='', heading='Video Page URL')
    if url != '' and len(url) > 0:
        item = ListItem.from_dict(path=plugin.url_for(endpoint=play, url=url))
        item.set_is_playable(True)
        item.set_info(type='video', info_labels={'Title': url, 'Plot': url})
        item.add_stream_info(stream_type='video', stream_values={})
        play(url)


@plugin.route('/saved')
def saved():
    litems = []
    sitems = []
    sitems = loadsaved()
    noitem = {'label': "No Saved Shows", 'icon': 'DefaultFolder.png', 'path': plugin.url_for('index')}
    if len(sitems) < 1:
        return [noitem]
    else:
        return sitems


@plugin.route('/saveshow/<name>/<link>')
def saveshow(name='', link=''):
    sitems = []
    litems = []
    try:
        savedpath = path.join(__datadir__, "saved.json")
        if path.exists(savedpath):
            fpin = file(savedpath)
            rawjson = fpin.read()
            sitems = json.loads(rawjson)
            fpin.close()
        saveitem = {'label': name, 'path': plugin.url_for(endpoint=category, name=name, url=link)}
        saveitem.setdefault(saveitem.keys()[0])
        sitems.insert(0, saveitem)
        fpout = file(savedpath, mode='w')
        json.dump(sitems, fpout)
        fpout.close()
        plugin.notify(msg="SAVED {0}".format(name), title=link)
    except:
        plugin.notify(msg="ERROR save failed for {0}".format(name), title=link)


@plugin.route('/removeshow/<name>/<link>')
def removeshow(name='', link=''):
    sitems = []
    litems = []
    sitems = loadsaved()
    for item in sitems:
        if item.get('name') == name or item.get('link') == link:
            plugin.notify(title='Removed {0}'.format(name), msg='Removed "{0}": {1}'.format(name, link))
        else:
            litems.append(item)
    jsout = json.dumps(litems)
    plugin.addon.setSetting('savedshows', jsout)
    plugin.notify(title='Removed {0}'.format(name), msg='{0} Removed Show link: {1}'.format(name, link))


def DL(url):
    html = u''
    html = getWeb.getSource(url, form_data=None, referer=__BASEURL__, xml=False, mobile=False).encode('latin', errors='ignore')
    return html


def formatshow(name=""):
    epname = name.replace('&#8211;', '-')
    epnum = ''
    epname = ''
    epdate = ''
    numparts = re.compile(r'[Ss]\d+[Ee]\d+').findall(name)
    if len(numparts) > 0:
        epnum = numparts.pop()
    datematch = re.compile(r'[12][0-9][0-9][0-9].[0-9][0-9]?.[0-9][0-9]?').findall(name)
    if len(datematch) > 0:
        epdate = datematch[0]
    name = name.replace('  ', ' ').strip()
    name = name.replace(epnum, '').strip()
    name = name.replace(epdate, '').strip()
    if epdate == '':
        # Let's see if we can find the date in the form of a string of Month_Abbr Daynum Year
        try:
            from calendar import month_abbr, month_name
            monthlist = month_name[:]
            monthlist.extend(month_abbr)
            monthlist.pop(13)
            monthlist.pop(0)
            regex = "{0}.(\d\d).(\d\d\d\d)"
            nummonth = 1
            for mon in monthlist:
                matches = re.compile(regex.format(mon)).findall(name)
                if len(matches) > 0:
                    day, year = matches.pop()
                    if nummonth < 10:
                        epdate = "{0} 0{1} {2}".format(year, nummonth, day)
                    else:
                        epdate = "{0} {1} {2}".format(year, nummonth, day)
                    name = name.replace(mon, '').strip()
                    name = name.replace(year, '').strip()
                    name = name.replace(day, '').strip()
                    break
                nummonth += 1
                if nummonth > 12: nummonth = 1
            if epdate == '':
                year = re.split(r'\d\d\d\d', name, 1)[0]
                epdate = name.replace(year, '').strip()
                name = name.replace(epdate, '').strip()
        except:
            pass
    epname = name.replace('(','').replace(')','').strip()
    epdate = epdate.replace('(','').replace(')','').strip()
    epnum = epnum.replace('(','').replace(')','').strip()
    return epname.strip(), epdate.strip(), epnum.strip()


def formatlabel(epname, epdate, epnum):
    eplbl = ''
    epname = epname.replace('!', '')
    try:
        if len(epdate) == 0 and len(epnum) == 0:
            return epname
        else:
            if len(epdate) > 0 and len(epnum) > 0:
                eplbl = "{0} ([COLOR blue]{1}[/COLOR] [COLOR cyan]{2}[/COLOR])".format(epname, epdate, epnum)
            else:
                if len(epdate) > 0:
                    eplbl = "{0} ([COLOR blue]{1}[/COLOR])".format(epname, epdate)
                else:
                    eplbl = "{0} ([COLOR cyan]{1}[/COLOR])".format(epname, epnum)
    except:
        eplbl = epname + ' ' + epdate + ' ' + epnum
    return eplbl


def findepseason(epnum):
    numseason = ''
    numep = ''
    parts = epnum.lower().split('e', 1)
    numseason = parts[0].replace('s', '').strip()
    numep = parts[-1].replace('e', '').strip()
    return numseason, numep


def episode_makeitem(episodename, episodelink):
    '''
    Will return a ListItem for the given link to an episode and it's full linked name.
    Name will be sent to format show to attempt to parse out a date or season from the title.
    Infolabels are populated with any details that can be parsed from the title as well.
    Should be used anytime an item needs to be created that is an item for one specific episode of a show.
    Latest 350, Saved Show, Category (Show listing of all episodes for that series) would all use this.
    '''
    infolbl = {}
    spath = plugin.url_for(episode, name=episodename, url=episodelink)
    img = "DefaultVideoFolder.png"
    seasonstr = ''
    try:
        eptitle, epdate, epnum = formatshow(episodename)
        eplbl = formatlabel(eptitle, epdate, epnum)
        plotstr = "{0} ({1}): {2} {3}".format(epdate, epnum, eptitle, episodelink)
        infolbl = {'Date': epdate, 'Title': eptitle, 'Plot': plotstr}
        if len(epnum) > 0:
            showS, showE = findepseason(epnum)
            dictshow = {'Episode': showE, 'Season': showS}
            infolbl.update(dictshow)
            snum = int(showS)
            epnum = int(showE)
            if snum > 0 and epnum > 0:
                epdate = "S{0}e{1}".format(snum, epnum)
        item = {'label': eplbl, 'label2': epdate, 'icon': img, 'thumbnail': img, 'path': spath}
        item.setdefault(item.keys()[0])
        li = ListItem.from_dict(**item)
        li.set_info(type='video', info_labels=infolbl)
        li.add_context_menu_items([('Search [B]{0}[/B]'.format(eptitle), 'RunPlugin({0})'.format(plugin.url_for(query, searchquery=eptitle)),)])
    except:
        li = ListItem(label=episodename, label2=episodelink, icon=img, thumbnail=img, path=spath)
    return li


@plugin.route('/latest')
def latest():
    url = __BASEURL__ + '/last-350-episodes'
    html = DL(url)
    matches = re.compile(ur'href="(http.+watchseries-online.+/episode.+?[^"])".+?</span>(.+?[^<])</a>', re.DOTALL + re.S + re.U).findall(html)
    litems = []
    epdate = ''
    eptitle = ''
    for eplink, epname in matches:
        litems.append(episode_makeitem(epname, eplink))
    return litems


@plugin.route('/search')
def search():
    searchtxt = ''
    searchtxt = plugin.get_setting('lastsearch')
    searchtxt = plugin.keyboard(searchtxt, 'Search All Sites', False)
    searchquery = searchtxt.replace(' ', '+')
    plugin.set_setting(key='lastsearch', val=searchtxt)
    return query(searchquery)


@plugin.route('/query/<searchquery>')
def query(searchquery):
    urlsearch = __BASEURL__ + '/?s={0}&search='.format(searchquery)
    html = DL(urlsearch)
    htmlres = html.partition('<div class="ddmcc">')[2].split('</div>',1)[0]
    matches = re.compile(ur'href="(http.+watchseries-online.+/category.+?[^"])".+?[^>]>(.+?[^<])<.a>', re.DOTALL + re.S + re.U).findall(htmlres)
    litems = []
    for slink, sname in matches:
        litems.append(makecatitem(sname, slink))
    return litems


@plugin.route('/category/<name>/<url>')
def category(name, url):
    html = DL(url)
    banner = None
    try:
        banner = str(html.split('id="banner_single"', 1)[0].rpartition('src="')[2].split('"',1)[0])
        if banner.startswith('/'): banner = __BASEURL__ + banner
    except:
        pass
    if banner is None: banner = 'DefaultVideoFolder.png'
    matches = re.compile(ur"href='(http.+watchseries-online.+/episode.+?[^'])'.+?</span>(.+?[^<])</a>", re.DOTALL + re.S + re.U).findall(html)
    litems =[]
    for eplink, epname in matches:
        litems.append(episode_makeitem(epname, eplink))
    litems.sort(key=lambda litems : litems.label, reverse=True)
    return litems


def findvidlinks(html=''):
    matches = re.compile(ur'<div class="play-btn">.*?</div>', re.DOTALL).findall(html)
    vids = []
    for link in matches:
        url = re.compile(ur'href="(.+)">', re.DOTALL+re.S).findall(str(link))[0]
        if url is not None:
            host = str(url.lower().split('://', 1)[-1])
            host = host.replace('www.', '')
            host = str(host.split('.', 1)[0]).title()
            label = "{0} [COLOR blue]{1}[/COLOR]".format(host, url.rpartition('/')[-1])
            vids.append((label, url,))
    return vids


def sortSourceItems(litems=[]):
    try:
        litems.sort(key=lambda litems: litems['label'], reverse=False)
        sourceslist = []
        stext = plugin.get_setting('topSources')
        if len(stext) < 1:
            sourceslist.append('streamcloud')
            sourceslist.append('vidto')
            sourceslist.append('openload')
            sourceslist.append('thevideo')
        else:
            sourceslist = stext.split(',')
        sorteditems = []
        for sortsource in sourceslist:
            for item in litems:
                if str(item['label2']).find(sortsource) != -1: sorteditems.append(item)
        for item in sorteditems:
            try:
                litems.remove(item)
            except:
                pass
        sorteditems.extend(litems)
        return sorteditems
    except:
        plugin.notify(msg="ERROR SORTING: #{0}".format(str(len(litems))), title="Source Sorting", delay=20000)
        return litems


@plugin.route('/episode/<name>/<url>')
def episode(name, url):
    html = DL(url)
    litems = []
    linklist = findvidlinks(html)
    if len(linklist) > 0:
        for name, link in linklist:
            itempath = plugin.url_for(play, url=link)
            item = dict(label=name, label2=link, icon='DefaultFolder.png', thumbnail='DefaultFolder.png', path=itempath)
            item.setdefault(item.keys()[0])
            litems.append(item)
        vitems = sortSourceItems(litems)
        litems = []
        for li in vitems:
            item = ListItem.from_dict(**li)
            item.set_is_playable(True)
            item.set_info(type='video', info_labels={'Title': item.label, 'Plot': item.label2})
            item.add_stream_info(stream_type='video', stream_values={})
            litems.append(item)
    else:
        plugin.notify(msg="ERROR No links found for {0}".format(name), title=url)
    return litems


@plugin.route('/play/<url>')
def play(url):
    resolved = ''
    stream_url = ''
    item = None
    try:
        import urlresolver
        resolved = urlresolver.HostedMediaFile(url).resolve()
        if not resolved or resolved == False or len(resolved) < 1:
            resolved = urlresolver.resolve(url)
            if resolved is None or len(resolved) < 1:
                resolved = urlresolver.resolve(urllib.unquote(url))
        if len(resolved) > 1:
            plugin.notify(msg="PLAY {0}".format(resolved.split('.',1)[-1]), title="URLRESOLVER {0}".format(url.split('.',1)[-1]), delay=2000)
            plugin.set_resolved_url(resolved)
            item = ListItem.from_dict(path=resolved)
            item.add_stream_info('video', stream_values={})
            item.set_is_playable(True)
            return item
    except:
        resolved = ''
        plugin.notify(msg="URLResolver Failed {0}".format(resolved.split('.',1)[-1]), title="Trying..YOUTUBE-DL {0}".format(url.split('.',1)[-1]), delay=2000)
    try:
        import YDStreamExtractor
        info = YDStreamExtractor.getVideoInfo(url, resolve_redirects=True)
        resolved = info.streamURL()
        for s in info.streams():
            try:
                stream_url = s['xbmc_url'].encode('utf-8', 'ignore')
                xbmc.log(msg="**YOUTUBE-DL Stream found: {0}".format(stream_url))
            except:
                pass
        if len(stream_url) > 1:
            resolved = stream_url
        if len(resolved) > 1:
            plugin.notify(msg="PLAY {0}".format(resolved.split('.',1)[-1]), title="YOUTUBE-DL {0}".format(url.split('.',1)[-1]), delay=2000)
            plugin.set_resolved_url(resolved)
            item = ListItem.from_dict(path=resolved)
            item.add_stream_info('video', stream_values={})
            item.set_is_playable(True)
            return item
    except:
        plugin.notify(msg="YOUTUBE-DL Failed: {0}".format(resolved.split('.',1)[-1]), title="Can't play {0}".format(url.split('.',1)[-1]), delay=2000)

    if len(resolved) > 1:
        plugin.set_resolved_url(resolved)
        item = ListItem.from_dict(path=resolved)
        return item
    else:
        plugin.set_resolved_url() #url)
        #plugurl = 'plugin://plugin.video.live.streamspro/?url={0}'.format(urllib.quote_plus(url))
        #item = ListItem.from_dict(path=plugurl)
        #item.add_stream_info('video', stream_values={})
        #item.set_is_playable(True)
        #plugin.notify(msg="RESOLVE FAIL: {0}".format(url.split('.', 1)[-1]),title="Trying {0}".format(item.path.split('.', 1)[-1]), delay=2000)
        return None


if __name__ == '__main__':
    hostname = ''
    hostname = plugin.get_setting('setHostname')
    if len(hostname) > 1:
        hostname = hostname.strip()
        hostname = hostname.strip('/')
        if str(hostname).startswith('http'):
            __BASEURL__ = hostname
        else:
            __BASEURL__ = 'https://' + hostname
    plugin.run()
    plugin.set_content('movies')
    plugin.set_view_mode(0)
