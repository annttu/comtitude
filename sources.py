#!/usr/bin/python2.7
# encoding: utf-8
import re
import sys
import subprocess
import logging

sys.path.append("/opt/local/Library/Frameworks/Python.framework/Versions/2.7/lib/python2.7/site-packages/")
import gps

sys.path.append("/opt/local/Library/Frameworks/Python.framework/Versions/2.6/lib/python2.6/site-packages/")

import serial

error = re.compile("COMMAND NOT SUPPORT")

class Modem():

    def __init__(self, modem="/dev/cu.HUAWEIMobile-Pcui"):
        self.modem = modem
        self.console = logging.getLogger("console")
        self.ser = None
        self.open_serial()

    def open_serial(self):
        try:
            self.ser = serial.Serial(self.modem, 115200, timeout=2)
            self.empty_buffer()
            return True
        except serial.serialutil.SerialException:
            self.console.info("Modem busy or not available!")
            return

    def empty_buffer(self):
        while self.ser.inWaiting() > 10:
            self.ser.readline()
        return

    def is_connected(self):
        try:
            self.ser.readline()
            return True
        except:
            return False

    def get_operationmode(self):
        try:
            if self.ser is None:
                if self.open_serial() is None:
                    return
            self.empty_buffer()
            self.ser.write("AT^SYSINFO\r")
            lines = 0
            while lines < 10:
                line = self.ser.readline()
                # +CSQ: 10,99
                match = re.match("\^SYSINFO:([0-9]+),([0-9]+)", line)
                lines += 1
                if match is not None:
                    if int(match.group(2)) == 2:
                        return "GSM"
                    elif int(match.group(2)) == 3:
                        return "WCDMA"
                if error.match(line) is not None:
                    self.console.debug("Modem don't support AT^SYSINFO")
                    break
            return
        except serial.serialutil.SerialException:
            self.console.error("Error while using modem")
            return
        except IOError:
            return

    def get_cellid(self):
        retval = {}
        try:
            if self.ser is None:
                if self.open_serial() is None:
                    return
            self.empty_buffer()
            self.ser.write("AT+CGREG=2\r")
            cellid = 0
            lac = 0
            lines = 0
            self.empty_buffer()
            self.ser.write("AT+CGREG?\r")
            while lines < 20:
                line = self.ser.readline()
                match = re.match("\+CGREG: 2,1, ([0-9ABCDEF]+), ([0-9ABCDEF]+)", line)
                lines += 1
                if match is not None:
                    #print("%s %s" % (match.group(1), match.group(2)))
                    retval["location_area_code"] =  int(match.group(1), 16)
                    retval["cell_id"] = int(match.group(2), 16)
                    break
                if error.match(line) is not None:
                    self.console.error("Modem don't supporting AT+CGREG")
                    break

            if retval == {}:
                return
            lines = 0
            self.empty_buffer()
            self.ser.write("AT+COPS?\r")
            while lines < 10:
                line = self.ser.readline()
                match = re.match("\+COPS: 1,2,\"([0-9]+)\",2", line)
                lines += 1
                if match is not None:
                    retval["mobile_network_code"] = match.group(1)[3:]
                    retval["mobile_country_code"] = match.group(1)[0:3]
                    break
                if error.match(line) is not None:
                    self.console.error("Modem don't support AT+COPS?")
                    break
            retval["age"] = 0
            return [retval]

        except OSError or IOError:
            self.console.error("Error while getting cell-id")
            return
        except serial.serialutil.SerialException:
            self.console.error("Error while getting cell-id")
            return


    def get_csq(self):
        retval = {}
        try:
            if self.ser is None:
                return
            self.empty_buffer()
            self.ser.write("AT+CSQ\r")
            lines = 0
            while lines < 10:
                line = self.ser.readline()
                # +CSQ: 10,99
                match = re.match("\+CSQ: ([0-3]?[0-9]),([0-9]+)", line)
                lines += 1
                if match is not None:
                    return  (int(match.group(1)) * 2) - 113
                    break
                if error.match(line) is not None:
                    break
            return

        except OSError:
            self.console.error("Error while getting cell-id")
            return
        except serial.serialutil.SerialException:
            self.console.error("Error while getting cell-id")
            return

def get_wifi():
    console = logging.getLogger("console")
    json = []
    aps = subprocess.check_output("/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport /usr/sbin/airport -s", shell=True)
    for ap in aps.strip().split("\n")[1:]:
        try:
            mac, streight = ap[33:55].strip().split(" ",2)
            # {"mac_address" : "00:15:a5:8b:90:00", "signal_strength" : -78}
            json.append({"mac_address" : mac, "signal_strength" : int(streight), "age" : 0})
        except ValueError:
            console.error("Unknown error parsing wlan values")
    if len(json) > 0:
        return json
    else:
        return

def get_gps():
    console = logging.getLogger('console')
    console.debug('Getting location from gps')
    session = None
    try:
        session = gps.gps()
        session.stream(gps.WATCH_ENABLE|gps.WATCH_NEWSTYLE)
        #if len(session.satellites) == 0:
        #    log.debug('Gps has no satellites')
        #    return
        for i in range(0,5):
            console.debug('Try %s' % i)
            report = session.next()
            if 'lat' in report:
                console.debug('Got location from gps\n%s' % report)
                session.close()
                return {'latitude' : report['lat'], 'longitude' : report['lon'], 'accurancy' : report['alt'], 'provider' : 'gps'}
    except StopIteration:
        pass
    except:
        pass
    console.debug('Gps not available')
    if session:
        session.close()
    return