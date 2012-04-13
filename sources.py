#!/usr/bin/python2.7
# encoding: utf-8
import re
import sys
import subprocess
import logging

sys.path.append("/opt/local/Library/Frameworks/Python.framework/Versions/2.6/lib/python2.6/site-packages/")
import serial

error = re.compile("COMMAND NOT SUPPORT")

def open_serial():
    console = logging.getLogger("console")
    try:
        ser = serial.Serial("/dev/cu.HUAWEIMobile-Pcui", 115200, timeout=2)
        empty_buffer(ser)
        return ser
    except serial.serialutil.SerialException:
        console.error("Modem busy or not available!")
        return

def empty_buffer(ser):
    while ser.inWaiting() > 10:
        ser.readline()
    return

def get_operationmode():
    console = logging.getLogger("console")
    try:
        ser = open_serial()
        if ser is None:
            return
        ser.write("AT^SYSINFO\r")
        lines = 0
        while lines < 10:
            line = ser.readline()
            # +CSQ: 10,99
            match = re.match("\^SYSINFO:([0-9]+),([0-9]+)", line)
            lines += 1
            if match is not None:
                if int(match.group(2)) == 2:
                    ser.close()
                    return "GSM"
                elif int(match.group(2)) == 3:
                    ser.close()
                    return "WCDMA"
            if error.match(line) is not None:
                console.debug("Modem don't support AT^SYSINFO")
                break
        ser.close()
        return
    except serial.serialutil.SerialException:
        console.error("Error while using modem")
        return
def get_cellid():
    console = logging.getLogger("console")
    retval = {}
    try:
        ser = open_serial()
        if ser is None:
            return
        ser.write("AT+CGREG=2\r")
        cellid = 0
        lac = 0
        lines = 0
        empty_buffer(ser)
        ser.write("AT+CGREG?\r")
        while lines < 20:
            line = ser.readline()
            match = re.match("\+CGREG: 2,1, ([0-9ABCDEF]+), ([0-9ABCDEF]+)", line)
            lines += 1
            if match is not None:
                #print("%s %s" % (match.group(1), match.group(2)))
                retval["location_area_code"] =  int(match.group(1), 16)
                retval["cell_id"] = int(match.group(2), 16)
                break
            if error.match(line) is not None:
                console.error("Modem don't supporting AT+CGREG")
                break

        if retval == {}:
            ser.close()
            return

        lines = 0
        ser.write("AT+COPS?\r")
        while lines < 10:
            line = ser.readline()
            match = re.match("\+COPS: 1,2,\"([0-9]+)\",2", line)
            lines += 1
            if match is not None:
                retval["mobile_network_code"] = match.group(1)[3:]
                retval["mobile_country_code"] = match.group(1)[0:3]
                break
            if error.match(line) is not None:
                console.error("Modem don't support AT+COPS?")
                break

        ser.write("AT+CSQ\r")
        lines = 0
        while lines < 10:
            line = ser.readline()
            # +CSQ: 10,99
            match = re.match("\+CSQ: ([0-9]+),([0-9]+)", line)
            lines += 1
            if match is not None:
                retval["signal_strength"] =  (int(match.group(1)) * 2) - 113
                break
            if error.match(line) is not None:
                break
        retval["age"] = 0
        ser.close()
        return [retval]
    except OSError:
        console.error("Error while getting cell-id")
        #ser.close()
        return
    except serial.serialutil.SerialException:
        console.error("Error while getting cell-id")
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

