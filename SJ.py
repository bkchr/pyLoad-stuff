from module.plugins.Hook import Hook 
import feedparser, re, urllib, urllib2, httplib, codecs, base64, json
from module.network.RequestFactory import getURL 
from BeautifulSoup import BeautifulSoup
import smtplib
import pycurl

def getSeriesList(file):
    try:
        titles = []
        f = codecs.open(file, "rb", "utf-8")
        for title in f.read().splitlines():
            if len(title) == 0:
                continue
            title = title.replace(" ", ".")
            titles.append(title)
        f.close()
        return titles
    except UnicodeError:
        self.core.log.error("SJFetcher - Abbruch, es befinden sich ungueltige Zeichen in der Suchdatei!")
    except IOError:
        self.core.log.error("SJFetcher - Abbruch, Suchdatei wurde nicht gefunden!")
    except Exception, e:
        self.core.log.error("SJFetcher - Unbekannter Fehler: %s" %e)
    
def notifyPushover(api ='', msg=''):
    data = urllib.urlencode({
        'user': api,
        'token': 'aBGPe78hyxBKfRawhuGbzttrEaQ9rW',
        'title': 'pyLoad: SJHook added Package',
        'message': "\n\n".join(msg)
    })
    try:
        req = urllib2.Request('https://api.pushover.net/1/messages.json', data)
        response = urllib2.urlopen(req)
    except urllib2.HTTPError:
        print 'Failed much'
        return False
    res = json.load(response)
    if res['status'] == 1:
        print 'Pushover Success'
    else:
        print 'Pushover Fail' 
    
def notifyPushbullet(api='', msg=''):
    data = urllib.urlencode({
        'type': 'note',
        'title': 'pyLoad: SJHook added Package',
        'body': "\n\n".join(msg)
    })
    auth = base64.encodestring('%s:' %api).replace('\n', '')
    try:
        req = urllib2.Request('https://api.pushbullet.com/v2/pushes', data)
        req.add_header('Authorization', 'Basic %s' % auth)
        response = urllib2.urlopen(req)
    except urllib2.HTTPError:
        print 'Failed much'
        return False
    res = json.load(response)
    if res['sender_name']:
        print 'Pushbullet Success'
    else:
        print 'Pushbullet Fail'

class SJ(Hook):
    __name__ = "SJ"
    __version__ = "1.52"
    __description__ = "Findet und fuegt neue Episoden von SJ.org pyLoad hinzu"
    __config__ = [("activated", "bool", "Aktiviert", "False"),
                  ("regex","bool","Eintraege aus der Suchdatei als regulaere Ausdruecke behandeln", "False"),
                  ("quality", """480p;720p;1080p""", "480p, 720p oder 1080p", "720p"),
                  ("file", "file", "Datei mit Seriennamen", "SJ.txt"),
                  ("rejectlist", "str", "Titel ablehnen mit (; getrennt)", "dd51;itunes"),
                  ("language", """DEUTSCH;ENGLISCH""", "Sprache", "DEUTSCH"),
                  ("interval", "int", "Interval", "60"),
                  ("hoster", """ul;so;fm;cz;alle""", "ul.to, filemonkey, cloudzer, share-online oder alle", "ul"),
                  ("pushoverapi", "str", "deine pushoverapi api", ""),
                  ("queue", "bool", "Direkt in die Warteschlange?", "False"),
                  ("pushbulletapi","str","Your Pushbullet-API key","")]
    __author_name__ = ("gutz-pilz","zapp-brannigan")
    __author_mail__ = ("unwichtig@gmail.com","")
    
    def coreReady(self):
        self.core.api.setConfigValue("SerienjunkiesOrg", "changeNameSJ", "Packagename", section='plugin')
        self.core.api.setConfigValue("SerienjunkiesOrg", "changeNameDJ", "Packagename", section='plugin')

    def setup(self):
        self.interval = self.getConfig("interval") * 60

    def periodical(self):
        feed = feedparser.parse('http://serienjunkies.org/xml/feeds/episoden.xml')
        
        self.pattern = "|".join(getSeriesList(self.getConfig("file"))).lower()
        reject = self.getConfig("rejectlist").replace(";","|").lower() if len(self.getConfig("rejectlist")) > 0 else "^unmatchable$"
        self.quality = self.getConfig("quality")
        self.hoster = self.getConfig("hoster")
        if self.hoster == "alle":
            self.hoster = "."
        self.added_items = []
        
        for post in feed.entries:
            link = post.link
            title = post.title
            
            if self.getConfig("regex"):
                m = re.search(self.pattern,title.lower())
                if not m and not "720p" in title and not "1080p" in title:
                    m = re.search(self.pattern.replace("480p","."),title.lower())
                    self.quality = "480p"
                if m:
                    if "720p" in title.lower(): self.quality = "720p"
                    if "1080p" in title.lower(): self.quality = "1080p"
                    m = re.search(reject,title.lower())
                    if m:
                        self.core.log.debug("SJFetcher - Abgelehnt: " + title)
                        continue
                    title = re.sub('\[.*\] ', '', post.title)
                    self.range_checkr(link,title)
                                
            else:
                if self.getConfig("quality") != '480p':
                    m = re.search(self.pattern,title.lower())
                    if m:
                        if self.getConfig("language") in title:
                            mm = re.search(self.quality,title.lower())
                            if mm:
                                mmm = re.search(reject,title.lower())
                                if mmm:
                                    self.core.log.debug("SJFetcher - Abgelehnt: " + title)
                                    continue
                                title = re.sub('\[.*\] ', '', post.title)
                                self.range_checkr(link,title)
        
                else:
                    m = re.search(self.pattern,title.lower())
                    if m:
                        if self.getConfig("language") in title:
                            if "720p" in title.lower() or "1080p" in title.lower():
                                continue
                            mm = re.search(reject,title.lower())
                            if mm:
                                self.core.log.debug("SJFetcher - Abgelehnt: " + title)
                                continue
                            title = re.sub('\[.*\] ', '', post.title)

        if len(self.getConfig('pushbulletapi')) > 2:
            notifyPushbullet(self.getConfig("pushbulletapi"),self.added_items) if len(self.added_items) > 0 else True
        if len(self.getConfig('pushoverapi')) > 2:
            notifyPushover(self.getConfig("pushoverapi"),self.added_items) if len(self.added_items) > 0 else True  
                    
    def range_checkr(self, link, title):
        pattern = re.match(".*S\d{2}E\d{2}-\w?\d{2}.*", title)
        if pattern is not None:
            range0 = re.sub(r".*S\d{2}E(\d{2}-\w?\d{2}).*",r"\1", title).replace("E","")
            number1 = re.sub(r"(\d{2})-\d{2}",r"\1", range0)
            number2 = re.sub(r"\d{2}-(\d{2})",r"\1", range0)
            title_cut = re.sub(r"(.*S\d{2}E).*",r"\1",title)
            for count in range(int(number1),(int(number2)+1)):
                NR = re.match("d\{2}", str(count))
                if NR is not None:
                    title1 = title_cut + str(count)
                    self.range_parse(link, title1)
                else:
                    title1 = title_cut +"0"+ str(count)
                    self.range_parse(link, title1)
        else:
            self.parse_download(link, title)


    def range_parse(self,series_url, search_title):
        req_page = getURL(series_url)
        soup = BeautifulSoup(req_page)
        titles = soup.findAll(text=re.compile(search_title))
        for title in titles:
           if self.quality !='480p' and self.quality in title: 
               self.parse_download(series_url, title)
           if self.quality =='480p' and not (('.720p.' in title) or ('.1080p.' in title)):               
               self.parse_download(series_url, title)


    def parse_download(self,series_url, search_title):
        req_page = getURL(series_url)
        soup = BeautifulSoup(req_page)
        title = soup.find(text=re.compile(search_title))
        if title:
            items = []
            links = title.parent.parent.findAll('a')
            for link in links:
                url = link['href']
                pattern = '.*%s_.*' % self.hoster
                if re.match(pattern, url):
                    items.append(url)
            self.send_package(title,items) if len(items) > 0 else True
                 
    def send_package(self, title, link):
        storage = self.getStorage(title)
        if storage == 'downloaded':
            self.core.log.debug("SJFetcher - " + title + " already downloaded")
        else:
            self.core.log.info("SJFetcher - NEW EPISODE: " + title)
            self.setStorage(title, 'downloaded')
            self.core.api.addPackage(title.encode("utf-8"), link, 1 if self.getConfig("queue") else 0)
            self.added_items.append(title.encode("utf-8"))
