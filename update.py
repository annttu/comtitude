#!/usr/bin/python2.7
# encoding: utf-8

import json
import sources
import urllib, urllib2
from latitude.latitude import setLocation
from time import sleep

def getPage(url, jdata=None):
    opener = urllib2.build_opener()
    headers = {'User-agent' : 'Mozilla/5.0 Macintosh Intel Mac OS X 10_7_3 AppleWebKit/535.11 KHTML, like Gecko Chrome/17.0.963.83 Safari/535.11','Content-Type': 'application/json'}
    if jdata is not None:
        data = json.dumps(jdata)
        request = urllib2.Request(url, data, headers)
    else:
        request = urllib2.Request(url, None, headers)
    return urllib2.urlopen(request).read()



def updateLocation():
    jdata = {"version": "1.1.0", "request_address": "true","host": "maps.google.com","address_language": "en_GB"}
    wifi_towers = sources.get_wifi()
    if wifi_towers != []:
        jdata["wifi_towers"] = wifi_towers
    else:
        cell_towers = sources.get_cellid()
        if cell_towers != []:
            jdata["cell_towers"] = cell_towers
        else:
            print("Cannot get location, switch wlan or USB modem on")
    #print("%s" % json.dumps(jdata))
    #print("%s" % getPage("http://127.0.0.1:8080", jdata))
    retval = json.loads(getPage("http://www.google.com/loc/json", jdata))
    #print("%s" % retval)
    if "location" in retval:
        setLocation(float(retval["location"]["latitude"]), float(retval["location"]["longitude"]), float(retval["location"]["accuracy"]))


if __name__ == "__main__":
    while True:
        updateLocation()
        sleep(360)

