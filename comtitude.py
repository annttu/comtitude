#!/usr/bin/env python
# encoding: utf-8

# comtitude
# Orginally created by Antti 'Annttu' Jaakkola
# Licensed under MIT licese, use as you wish

import json
import urllib, urllib2
from time import sleep
from datetime import datetime
import re
import getopt
import sys
import logging
logging.basicConfig(format='%(asctime)-6s %(levelname)s: %(message)s')

# my libraries
import google
import sources
from tools import *

def usage():
        print("Usage: [-h, --help show help|-f --wifi wifi only|-m --modem usb modem only] " + \
        "[-o --once run once only] [-d --delay between updates] " +\
        "[-t --try don't update to latitude] [-v --verbose |--debug]" +\
        "[-c --coordinates 12.345656,32.123456 |-a --address Fabianinkatu 1, Helsinki, Finland]")
        return

latitude = re.compile("lat=\"([0-9]+\.[0-9]+)\"")
longitude = re.compile("lon=\"([0-9]+\.[0-9]+)\"")
accurancy = re.compile("range=\"([0-9]+)\"")
latlon = re.compile('([0-9]{1,2}\.[0-9]{2,10}),([0-9]{1,2}\.[0-9]{2,10})')

class Comtitude:

    def __init__(self):
        self.log = logging.getLogger('self.log')
        self.log.setLevel(logging.WARNING)
        self.modem = None
        self.once = False
        self.cell = True
        self.wifi = True
        self.delay = 360
        self.update = True
        self.address = None
        self.location = None
        self.loc = None
        self.last = None
        self.verbose = 0

    def opencellid(self, jdata, update=False):
        """Get location from opencellid
        if update is true, add cell_tower to opencellid instead of getting location"""
        loc = {}
        if "cell_towers" not in jdata:
            return
        if "mobile_country_code" not in jdata["cell_towers"][0] or "cell_id" not in jdata["cell_towers"][0]:
            return
        if update:
            if 'location' in jdata:
                print("http://www.opencellid.org/measure/add?key=2d895f16e677ec097d52c4faddcc92ce&mnc=%s&mcc=%s&lac=%s&cellid=%s&lat=%s&lon=%s" % (
                            jdata["cell_towers"][0]["mobile_country_code"], jdata["cell_towers"][0]["mobile_network_code"],
                            jdata["cell_towers"][0]["location_area_code"], jdata["cell_towers"][0]["cell_id"],
                            jdata['location']['latitude'], jdata['location']['longitude']))
                data = getPage("http://www.opencellid.org/measure/add?key=2d895f16e677ec097d52c4faddcc92ce&mnc=%s&mcc=%s&lac=%s&cellid=%s&lat=%s&lon=%s" % (
                            jdata["cell_towers"][0]["mobile_country_code"], jdata["cell_towers"][0]["mobile_network_code"],
                            jdata["cell_towers"][0]["location_area_code"], jdata["cell_towers"][0]["cell_id"],
                            jdata['location']['latitude'], jdata['location']['longitude']))
                self.log.debug('added current cellid to opencellid: %s' % data)
            else:
                self.log.info('Cannot add to opencellid, no current location given')
            return
        data = getPage("http://www.opencellid.org/cell/get?key=2d895f16e677ec097d52c4faddcc92ce&mnc=%s&mcc=%s&lac=%s&cellid=%s" % (jdata["cell_towers"][0]["mobile_country_code"], jdata["cell_towers"][0]["mobile_network_code"], jdata["cell_towers"][0]["location_area_code"], jdata["cell_towers"][0]["cell_id"]))
        if data is not None:
            self.log.debug("Got response from opencellid\n%s" % data)
            l = latitude.search(data)
            if l is not None:
                loc["latitude"] = float(l.group(1))
            else:
                return
        else:
            self.log.warning("Cannot get location from opencellid")
            return
        l = longitude.search(data)
        if l is not None:
            loc["longitude"] = float(l.group(1))
        l = accurancy.search(data)
        if l is not None:
            loc["accurancy"] = float(l.group(1))
        if loc["accurancy"] > 10000:
            self.log.warning("opencellid range too big")
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


    def glocation(self, jdata):
        retval = {}
        loc = json.loads(getPage("http://www.google.com/loc/json", jdata))
        if "location" in loc:
            self.log.debug("got resonse from google\n%s" % loc)
            retval["latitude"] = float(loc["location"]["latitude"])
            retval["longitude"] = float(loc["location"]["longitude"])
            try:
                retval["accurancy"] = float(loc["location"]["accurancy"])
            except KeyError:
                retval["accurancy"] = 30.0
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
                self.log.warning("Cannot get response from google")
                retval["street_number"] = ""
                retval["street_number"] = ""
                retval["city"] = ""
                retval["country"] = ""
            retval["provider"] = "google"
            if retval["accurancy"] > 10000:
                self.log.warning("google give too big range: %s" % retval["accurancy"])
                return
            return retval


    def updateLocation(self):
        jdata = {
            "version": "1.1.0",
            "request_address": "true",
            "host": "maps.google.com",
            "address_language": "fi_FI"
        }
        wifi_towers = None
        cell_towers = None
        gps = sources.get_gps()
        if self.wifi is True:
            wifi_towers = sources.get_wifi()
        count_wifi_towers = 0
        count_cell_towers = 0
        if wifi_towers is not None:
            count_wifi_towers = len(wifi_towers)
            jdata["wifi_towers"] = wifi_towers
        if self.cell is True and self.modem is not None:
            mode = self.modem.get_operationmode()
            if mode is not None:
                jdata["radio_type"] = mode
            cell_towers = self.modem.get_cellid()
            if cell_towers is not None:
                count_cell_towers = len(cell_towers)
                jdata["cell_towers"] = cell_towers
        if gps is not None:
            jdata['location'] = {
            'latitude' : gps['latitude'],
            'longitude' : gps['longitude'],
            'accurancy' : gps['accurancy']
            }
            # update cell_towers to opencelli
            self.opencellid(jdata, update=True)
        if gps is None and wifi_towers is None and cell_towers is None:
            self.log.warning("Cannot get location, switch wlan or USB modem on")
            return
        self.log.debug("%s" % json.dumps(jdata))
        loc = getPage("http://www.google.com/loc/json", jdata)
        if loc is not None:
            loc = json.loads(loc)
            loc = self.glocation(jdata)
            if not loc:
                loc = self.opencellid(jdata)
        if gps:
            retval = google.location2latitude(gps["latitude"], gps["longitude"], gps["accurancy"])
            self.log.debug("latitude retval: %s" % retval)
            gps["count_wifi_towers"] = count_wifi_towers;
            gps["count_cell_towers"] = count_cell_towers;
            self.last = datetime.now()
            return gps
        elif loc is not None:
            retval = google.location2latitude(loc["latitude"], 
                            loc["longitude"], loc["accurancy"])
            self.log.debug("latitude retval: %s" % retval)
            loc["count_wifi_towers"] = count_wifi_towers;
            loc["count_cell_towers"] = count_cell_towers;
            self.last = datetime.now()
            return loc
        else:
            self.log.warning("Cannot get current location")
        return

    def formatOutput(self):
        if self.loc is None:
            return
        self.log.info("Location updated using %s wifi towers and %s cell towers" % (
                self.loc["count_wifi_towers"], self.loc["count_cell_towers"]))
        if "street" in self.loc:
            self.log.info("Your location based on %s: %s,%s acc: %sm; address: %s %s, %s, %s" % (
                self.loc["provider"], self.loc["latitude"], self.loc["longitude"],
                self.loc["accurancy"], self.loc["street"], self.loc["street_number"],
                self.loc["city"], self.loc["country"]))
        else:
            self.log.info("Your location based on %s: %s,%s acc: %sm" % (
                self.loc["provider"], self.loc["latitude"], self.loc["longitude"], self.loc["accurancy"]))

    def status(self):
        if not self.loc:
            return 'No location available'
        if 'street' in self.loc:
            return "%s %s, %s" % (self.loc["street"], self.loc["street_number"],
                                  self.loc["city"])
        else:
            return "%s, %s" % (self.loc["latitude"], self.loc["longitude"])

    def last_updated(self):
        if not self.last:
            return 'Time'
        else:
            return self.last.strftime('%d.%m.%Y %H:%M')

    def getLocationByAddress(self, address):
            qn = address.split(' ')
            q = '+'.join(qn)
            url = "http://maps.googleapis.com/maps/api/geocode/json?address=" + q + "&sensor=false"
            retval = json.loads(getPage(url))
            self.log.debug("geocode output: %s" % retval)
            if "status" in retval:
                if retval["status"] !=  "OK":
                    self.log.error("Got error %s from google" % retval["status"])
                    return
            if "results" in retval:
                if "geometry" in retval["results"][0]:
                    lat = retval["results"][0]["geometry"]["location"]["lat"]
                    lon = retval["results"][0]["geometry"]["location"]["lng"]
                    return [lat, lon]
            return

    def _update(self):
        if self.modem and self.modem.is_connected() is False:
            self.log.info("Modem is not connected anymore")
            self.modem = None

        if self.cell and self.modem is None:
            self.modem = sources.Modem()
        try:
            self.loc = self.updateLocation()
            self.formatOutput()
        except KeyboardInterrupt:
            return
        except Exception as e:
            print("Unexepted Error occured")
            import traceback
            self.log.critical(traceback.format_exc(e))
        except:
            self.log.critical("Unexepted unknown error occured")

    def loop(self):
        """Main loop"""
        if self.address is not None:
            self.location = self.getLocationByAddress(self.address)
            self.once = True
            if self.location is None:
                self.log.error("Can't find this address")
                return
        if self.cell is False and self.wifi is False and self.location is None:
            self.log.error("Need either cellurar or wifi access")
            sys.exit(1)
        if self.location is not None:
            retval = google.location2latitude(self.location[0], self.location[1], 10)
            self.log.debug("latitude retval: %s" % retval)
            return
        while True:
            self._update()
            if self.once:
                break
            sleep(self.delay)

def main(args=[]):
    console = logging.getLogger("console")
    comtitude = Comtitude()
    if len(args) > 0:
        try:
            opts, args = getopt.getopt(args, "hfmovd:ta:c:",
                ["help", "wifi", "cell", "once", "delay", "try",
                "verbose", "debug", "address", "coordinates"])
            comtitude.once = False
        except Exception as error:
            print("%s" % error)
            usage()
            sys.exit(1)
        for opt, arg in opts:
            if opt in ("-h", "--help"):
                usage()
                return
            elif opt in ("-f", "--wifi"):
                comtitude.cell = False
            elif opt in ("-m", "--modem"):
                comtitude.wifi = False
            elif opt in ("-o", "--once"):
                comtitude.once = True
            elif opt in ("-t", "--try"):
                comtitude.update = False
            elif opt in ("-v", "--verbose"):
                comtitude.log.setLevel(logging.INFO)
            elif opt == "--debug":
                comtitude.log.setLevel(logging.DEBUG)
            elif opt in ("--coordinates", "-c"):
                if latlon.match(arg) is None:
                    comtitude.location = []
                    comtitude.location.append(arg.split(",")[0])
                    comtitude.location.append(arg.split(",")[1])
                    comtitude.once = True
                else:
                    console.error("Wrong coordinate syntax")
                    sys.exit(1)
            elif opt in ("--address", "-a"):
                comtitude.address = arg
            elif opt in ("-d", "--delay"):
                if int(arg) > 5:
                    comtitude.delay = int(arg)
                else:
                    print("delay too small!")
                    return
    comtitude.loop()

if __name__ == '__main__':
    main(sys.argv[1:])