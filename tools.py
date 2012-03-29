# helperfunctions

import urllib2
import json


def getPage(url, jdata=None):
    opener = urllib2.build_opener()
    headers = {'User-agent' : 'Mozilla/5.0 Macintosh Intel Mac OS X 10_7_3 AppleWebKit/535.11 KHTML, like Gecko Chrome/17.0.963.83 Safari/535.11','Content-Type': 'application/json'}
    if jdata is not None:
        data = json.dumps(jdata)
        request = urllib2.Request(url, data, headers)
    else:
        request = urllib2.Request(url, None, headers)
    return urllib2.urlopen(request).read()
