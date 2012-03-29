#!/usr/bin/python2.7
# encoding: utf-8

import json
import sources
import urllib, urllib2
from time import sleep
import re
import getopt
import sys

# my libraries
import google
from tools import *

## Todo:
# opencellid add/measure
##

latitude = re.compile("lat=\"([0-9]+\.[0-9]+)\"")
longitude = re.compile("lon=\"([0-9]+\.[0-9]+)\"")
accurancy = re.compile("range=\"([0-9]+)\"")

def usage():
        print("Usage: [-h, --help show help|-f --wifi wifi only|-c --cell cellid only] [-o --once run once only] [-d --delay between updates]")
        return

def opencellid(jdata):
    loc = {}
    if "cell_towers" not in jdata:
        return
    data = getPage("http://www.opencellid.org/cell/get?key=2d895f16e677ec097d52c4faddcc92ce&mnc=%s&mcc=%s&lac=%s&cellid=%s" % (jdata["cell_towers"][0]["mobile_country_code"], jdata["cell_towers"][0]["mobile_network_code"], jdata["cell_towers"][0]["location_area_code"], jdata["cell_towers"][0]["cell_id"]))
    l = latitude.search(data)
    if l is not None:
        loc["latitude"] = float(l.group(1))
    else:
        return
    l = longitude.search(data)
    if l is not None:
        loc["longitude"] = float(l.group(1))
    l = accurancy.search(data)
    if l is not None:
        loc["accurancy"] = float(l.group(1))
    if loc["accurancy"] > 10000:
        print("opencellid range too big")
        return
    addr = google.latlon2address(loc["latitude"], loc["longitude"])
    if addr is not None:
        loc["street"] = addr["street"]
        loc["street_number"] = addr["street_number"]
        loc["city"] = addr["county"]
        loc["country"] = addr["country"]

    loc["provider"] = "opencellid"
    return loc


def glocation(jdata):
    retval = {}
    loc = json.loads(getPage("http://www.google.com/loc/json", jdata))
    print("\"%s\"" % loc)
    if "location" in loc:
        retval["latitude"] = float(loc["location"]["latitude"])
        retval["longitude"] = float(loc["location"]["longitude"])
        retval["accurancy"] = float(loc["location"]["accuracy"])
        retval["street"] = loc["location"]["address"]["street"]
        if "street_number" in loc["location"]["address"]:
            retval["street_number"] = loc["location"]["address"]["street_number"]
        else:
            retval["street_number"] = 0
        retval["city"] = loc["location"]["address"]["county"]
        retval["country"] = loc["location"]["address"]["country"]
        retval["provider"] = "google"
        if retval["accurancy"] > 10000:
            print("google range too big")
            return
        return retval


def updateLocation(wlan=True, cell=True):
    jdata = {
        "version": "1.1.0", 
        "request_address": "true",
        "host": "maps.google.com",
        "address_language": "fi_FI"
    }
    wifi_towers = None
    if wlan is True:
        wifi_towers = sources.get_wifi()
    count_wifi_towers = 0
    if wifi_towers is not None:
        count_wifi_towers = len(wifi_towers)
        jdata["wifi_towers"] = wifi_towers
    if cell is True:
        mode = sources.get_operationmode()
        if mode is not None:
            jdata["radio_type"] = mode
        cell_towers = sources.get_cellid()
        count_cell_towers = 0
        if cell_towers is not None:
            count_cell_towers = len(cell_towers)
            jdata["cell_towers"] = cell_towers
    #print("%s" % jdata)
    if wifi_towers is None and cell_towers is None:
        print("Cannot get location, switch wlan or USB modem on")
        return
    #print("%s" % json.dumps(jdata))
    #print("%s" % getPage("http://127.0.0.1:8080", jdata))
    loc = json.loads(getPage("http://www.google.com/loc/json", jdata))
    #print("%s" % loc)
    loc = glocation(jdata)
    if loc is not None:
        google.location2latitude(loc["latitude"], loc["longitude"], loc["accurancy"])
        loc["count_wifi_towers"] = count_wifi_towers;
        loc["count_cell_towers"] = count_cell_towers;
        return loc
    loc = opencellid(jdata)
    if loc is not None:
        google.location2latitude(loc["latitude"], loc["longitude"], loc["accurancy"])
        loc["count_wifi_towers"] = count_wifi_towers;
        loc["count_cell_towers"] = count_cell_towers;
        return loc
    print("Cannot get current location")
    return

def formatOutput(loc):
    if loc is not None:
        print("Location updated using %s wifi towers and %s cell towers" % (loc["count_wifi_towers"], loc["count_cell_towers"]))
        if "street" in loc:
            print("Your location based on %s: %s,%s acc: %sm; address: %s %s, %s, %s" % (loc["provider"], loc["latitude"], loc["longitude"], loc["accurancy"], loc["street"], loc["street_number"], loc["city"], loc["country"]))
        else:
            print("Your location based on google: %s,%s acc: %sm" % (loc["latitude"], loc["longitude"], loc["accurancy"]))


def main(args):
    cell = True
    wifi = True
    delay = 360
    if len(args) > 0:
        try:
            opts, args = getopt.getopt(args, "hfcod:", ["help", "wifi", "cell", "once", "delay"])
            once = False
        except:
            usage()
            sys.exit(1)
        for opt, arg in opts:
            if opt in ("-h", "--help"):
                usage()
                return
            elif opt in ("-f", "--wifi"):
                cell = False
            elif opt in ("-c", "--cell"):
                wifi = False
            elif opt in ("-o", "--once"):
                once = True
            elif opt in ("-d", "--delay"):
                if int(arg) > 5:
                    delay  = int(arg)
                else:
                    print("delay too small!")
                    return
        if cell is False and wifi is False:
            print("Need either cellurar or wifi access")
            sys.exit(1)
        if once:
            formatOutput(updateLocation(wifi, cell))
            return
    try:
        while True:
            formatOutput(updateLocation(wifi, cell))
            sleep(delay)
    except KeyboardInterrupt:
        print("Bye!")
        pass

if __name__ == "__main__":
    main(sys.argv[1:])

