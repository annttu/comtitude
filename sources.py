#!/usr/bin/python2.7
# encoding: utf-8
import re
import sys
import subprocess

sys.path.append("/opt/local/Library/Frameworks/Python.framework/Versions/2.6/lib/python2.6/site-packages/")
import serial

def get_cellid():
    retval = []
    ser = serial.Serial("/dev/cu.HUAWEIMobile-Pcui", 115200, timeout=2)
    ser.write("AT+CGREG=2\r")
    cellid = 0
    lac = 0
    lines = 0
    while lines < 80:
        if (lines % 5) == 0:
            ser.write("AT+CGREG?\r")
        line = ser.readline()
        match = re.match("\+CGREG: 2,1, ([0-9ABCDEF]+), ([0-9ABCDEF]+)", line)
        lines += 1
        if match is not None:
            print("%s %s" % (match.group(1), match.group(2)))
            lac = int(match.group(1), 16)
            if int(match.group(2), 16) < 65536:
                cellid = int(match.group(2), 16)
            else:
                cellid = int(match.group(2)[2:], 16)
            break
    if retval is {}:
        return

    mmc = 0
    mnc = 0
    lines = 0
    while lines < 80:
        if (lines % 10) == 0:
            ser.write("AT+COPS?\r")
        line = ser.readline()
        match = re.match("\+COPS: 1,2,\"([0-9]+)\",2", line)
        lines += 1
        if match is not None:
            mcc = match.group(1)[0:2]
            mnc = match.group(1)[2:]
            break
    if cellid != 0 and lac != 0:
        if mcc != 0 and mnc != 0:
            retval.append({"cell_id": cellid, "location_area_code": lac, "mobile_network_code": mnc, "mobile_country_code": mcc})
        else:
            retval.append({"cell_id": cellid, "location_area_code": lac})
    return retval

def get_wifi():
    json = []
    aps = subprocess.check_output("/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport /usr/sbin/airport -s", shell=True)
    for ap in aps.strip().split("\n")[1:]:
        mac, streight = ap[33:55].strip().split(" ",2)
        # {"mac_address" : "00:15:a5:8b:90:00", "signal_strength" : -78}
        json.append({"mac_address" : mac, "signal_strength" : int(streight)})
    return json

