#!/usr/bin/python2.7
# encoding: utf-8

import json
import sources
import urllib, urllib2
from time import sleep
import re
import getopt
import sys
import logging

# my libraries
import google
from tools import *

## Todo:
# opencellid add/measure
##

latitude = re.compile("lat=\"([0-9]+\.[0-9]+)\"")
longitude = re.compile("lon=\"([0-9]+\.[0-9]+)\"")
accurancy = re.compile("range=\"([0-9]+)\"")
latlon = re.compile('([0-9]{1,2}\.[0-9]{2,10}),([0-9]{1,2}\.[0-9]{2,10})')

logging.basicConfig(format='%(asctime)-6s %(levelname)s: %(message)s')
logger = logging.getLogger('console')
logger.setLevel(logging.WARNING)

def usage():
        print("Usage: [-h, --help show help|-f --wifi wifi only|-m --modem usb modem only] [-o --once run once only] [-d --delay between updates] [-t --try don't update to latitude] [-v --verbose |--debug] [-c --coordinates 12.345656,32.123456 |-a --address Fabianinkatu 1, Helsinki, Finland]")
        return

def opencellid(jdata):
    loc = {}
    console = logging.getLogger("console")
    if "cell_towers" not in jdata:
        return
    if "mobile_country_code" not in jdata["cell_towers"][0] or "cell_id" not in jdata["cell_towers"][0]:
        return
    data = getPage("http://www.opencellid.org/cell/get?key=2d895f16e677ec097d52c4faddcc92ce&mnc=%s&mcc=%s&lac=%s&cellid=%s" % (jdata["cell_towers"][0]["mobile_country_code"], jdata["cell_towers"][0]["mobile_network_code"], jdata["cell_towers"][0]["location_area_code"], jdata["cell_towers"][0]["cell_id"]))
    if data is not None:
        console.debug("Got response from opencellid\n%s" % data)
        l = latitude.search(data)
        if l is not None:
            loc["latitude"] = float(l.group(1))
        else:
            return
    else:
        console.warning("Cannot get location from opencellid")
        return
    l = longitude.search(data)
    if l is not None:
        loc["longitude"] = float(l.group(1))
    l = accurancy.search(data)
    if l is not None:
        loc["accurancy"] = float(l.group(1))
    if loc["accurancy"] > 10000:
        console.warning("opencellid range too big")
        return
    addr = google.latlon2address(loc["latitude"], loc["longitude"])
    if addr is not None:
        if "street" in addr:
            loc["street"] = addr["street"]
        else:
            loc["street"] = ""
        if "street_number" in addr:
            loc["street_number"] = addr["street_number"]
        else:
            loc["street_number"] = ""
        loc["city"] = addr["county"]
        loc["country"] = addr["country"]

    loc["provider"] = "opencellid"
    return loc


def glocation(jdata):
    console = logging.getLogger("console")
    retval = {}
    loc = json.loads(getPage("http://www.google.com/loc/json", jdata))
    #print("\"%s\"" % loc)
    if "location" in loc:
        console.debug("got resonse from google\n%s" % loc)
        retval["latitude"] = float(loc["location"]["latitude"])
        retval["longitude"] = float(loc["location"]["longitude"])
        retval["accurancy"] = float(loc["location"]["accuracy"])
        if "address" in loc["location"]:
            if "street" in loc["location"]["address"]:
                retval["street"] = loc["location"]["address"]["street"]
            else:
                retval["street"] = ""
            if "street_number" in loc["location"]["address"]:
                retval["street_number"] = loc["location"]["address"]["street_number"]
            else:
                retval["street_number"] = ""
            if "county" in loc["location"]["address"]:
                retval["city"] = loc["location"]["address"]["county"]
            else:
                retval["city"] = ""
            retval["country"] = loc["location"]["address"]["country"]
        else:
            console.warning("Cannot get response from google")
            retval["street_number"] = ""
            retval["street_number"] = ""
            retval["city"] = ""
            retval["country"] = ""
        retval["provider"] = "google"
        if retval["accurancy"] > 10000:
            console.warning("google give too big range: %s" % retval["accurancy"])
            return
        return retval


def updateLocation(wlan=True, cell=True):
    console = logging.getLogger("console")
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
    if wifi_towers is None and cell_towers is None:
        console.warning("Cannot get location, switch wlan or USB modem on")
        return
    console.debug("%s" % json.dumps(jdata))
    loc = getPage("http://www.google.com/loc/json", jdata)
    if loc is not None:
        loc = json.loads(loc)
        loc = glocation(jdata)
        if loc is not None:
            retval = google.location2latitude(loc["latitude"], loc["longitude"], loc["accurancy"])
            console.debug("latitude retval: %s" % retval)
            loc["count_wifi_towers"] = count_wifi_towers;
            loc["count_cell_towers"] = count_cell_towers;
            return loc
    loc = opencellid(jdata)
    if loc is not None:
        if update:
            retval = google.location2latitude(loc["latitude"], loc["longitude"], loc["accurancy"])
            console.debug("latitude retval: %s" % retval)
        loc["count_wifi_towers"] = count_wifi_towers;
        loc["count_cell_towers"] = count_cell_towers;
        return loc
    console.warning("Cannot get current location")
    return

def formatOutput(loc):
    console = logging.getLogger("console")
    if loc is not None:
        console.info("Location updated using %s wifi towers and %s cell towers" % (loc["count_wifi_towers"], loc["count_cell_towers"]))
        if "street" in loc:
            console.info("Your location based on %s: %s,%s acc: %sm; address: %s %s, %s, %s" % (loc["provider"], loc["latitude"], loc["longitude"], loc["accurancy"], loc["street"], loc["street_number"], loc["city"], loc["country"]))
        else:
            console.info("Your location based on %s: %s,%s acc: %sm" % (loc["provider"], loc["latitude"], loc["longitude"], loc["accurancy"]))

def getLocationByAddress(address):
        console = logging.getLogger("console")
        qn = address.split(' ')
        q = '+'.join(qn)
        url = "http://maps.googleapis.com/maps/api/geocode/json?address=" + q + "&sensor=false"
        retval = json.loads(getPage(url))
        console.debug("geocode output: %s" % retval)
        if "status" in retval:
            if retval["status"] !=  "OK":
                console.error("Got error %s from google" % retval["status"])
                return
        if "results" in retval:
            if "geometry" in retval["results"][0]:
                lat = retval["results"][0]["geometry"]["location"]["lat"]
                lon = retval["results"][0]["geometry"]["location"]["lng"]
                return [lat, lon]
        return

def main(args):
    console = logging.getLogger("console")
    cell = True
    wifi = True
    delay = 360
    update = True
    address = None
    location = None
    verbose = 0
    if len(args) > 0:
        try:
            opts, args = getopt.getopt(args, "hfmovd:ta:c:", ["help", "wifi", "cell", "once", "delay", "try", "verbose", "debug", "address", "coordinates"])
            once = False
        except Exception as error:
            print("%s" % error)
            usage()
            sys.exit(1)
        for opt, arg in opts:
            if opt in ("-h", "--help"):
                usage()
                return
            elif opt in ("-f", "--wifi"):
                cell = False
            elif opt in ("-m", "--modem"):
                wifi = False
            elif opt in ("-o", "--once"):
                once = True
            elif opt in ("-t", "--try"):
                update = False
            elif opt in ("-v", "--verbose"):
                console.setLevel(logging.INFO)
            elif opt == "--debug":
                console.setLevel(logging.DEBUG)
            elif opt in ("--coordinates", "-c"):
                if latlon.match(arg) is None:
                    location = []
                    location.append(arg.split(",")[0])
                    location.append(arg.split(",")[1])
                    once = True
                else:
                    console.error("Wrong coordinate syntax")
                    sys.exit(1)
            elif opt in ("--address", "-a"):
                address = arg
            elif opt in ("-d", "--delay"):
                if int(arg) > 5:
                    delay  = int(arg)
                else:
                    print("delay too small!")
                    return
        if address is not None:
            location = getLocationByAddress(arg)
            once = True
            if location is None:
                console.error("Can't find this address")
                return
        if cell is False and wifi is False and location is None:
            console.error("Need either cellurar or wifi access")
            sys.exit(1)
        if once:
            if location is not None:
                retval = google.location2latitude(location[0], location[1], 10)
                console.debug("latitude retval: %s" % retval)
                return
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

