# encoding: utf-8

# some helperfunctions for googleapi

#
#http://maps.googleapis.com/maps/api/geocode/json?latlng=60.56245,24.9475585&sensor=false

import sys
from os import environ

home = environ["HOME"]

sys.path.append("/opt/local/Library/Frameworks/Python.framework/Versions/2.6/lib/python2.6/site-packages/")
sys.path.append("/opt/local/Library/Frameworks/Python.framework/Versions/2.6/lib/python2.6/site-packages/oauth2-1.5.211-py2.6.egg/")
sys.path.append("/opt/local/Library/Frameworks/Python.framework/Versions/2.6/lib/python2.6/site-packages/python_gflags-2.0-py2.6.egg/")
sys.path.append("/opt/local/Library/Frameworks/Python.framework/Versions/2.6/lib/python2.6/site-packages/google_api_python_client-1.0beta8-py2.6.egg") 

import httplib2

from apiclient.discovery import build
from apiclient.oauth import FlowThreeLegged
from apiclient.ext.authtools import run
from apiclient.ext.file import Storage

import json
from tools import getPage

def latlon2address(lat,lon):
    q = ",".join([str(lat),str(lon)])
    retval = {}
    page = getPage("http://maps.googleapis.com/maps/api/geocode/json?latlng=%s&sensor=true&language=FI" % q)
    jdata = json.loads(page)
    if "results" not in jdata:
        return
    if len(jdata["results"]) < 1:
        return

    for component in jdata["results"]:
         for item in component["address_components"]:
            if "administrative_area_level_3" in item["types"]:
                retval["city"] = item["long_name"]
            elif "country" in item["types"]:
                retval["country"] = item["long_name"]
            elif "postal_code" in item["types"]:
                retval["postal_code"] = item["long_name"]
            elif "administrative_area_level_1" in item["types"]:
                retval["administrative_area_level_1"] = item["long_name"]
            elif "route" in item["types"]:
                retval["street"] = item["long_name"]
            elif "street_number" in item["types"]:
                retval["street_number"] = int(item["long_name"])
    if retval != {}:
        return retval

def location2latitude(lat, lon, acc=130):
  storage = Storage(home + '/.latitude.dat')
  credentials = storage.get()
  if credentials is None or credentials.invalid == True:
    auth_discovery = build("latitude", "v1").auth_discovery()
    flow = FlowThreeLegged(auth_discovery,
           # https://www.google.com/accounts/ManageDomains
           consumer_key='annttu.fi',
           consumer_secret='yAVn-cmYaqQOC59yTikkeDLw',
           user_agent='Comtitude/1.0',
           domain='annttu.fi',
           scope='https://www.googleapis.com/auth/latitude',
           xoauth_displayname='Google API Latitude Example',
           location='current',
           granularity='city'
           )

    credentials = run(flow, storage)

  http = httplib2.Http()
  http = credentials.authorize(http)

  service = build("latitude", "v1", http=http)

  body = {
      "data": {
          "kind": "latitude#location",
          "latitude": lat,
          "longitude": lon,
          "accuracy": acc,
          "altitude": 0
          }
      }
  return service.currentLocation().insert(body=body).execute()
