# encoding: utf-8

# some helperfunctions for googleapi

#
#http://maps.googleapis.com/maps/api/geocode/json?latlng=60.56245,24.9475585&sensor=false

import sys
from os import environ, path
import googledata

home = environ["HOME"]

import httplib2

from apiclient.discovery import build
from oauth2client.file import Storage
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import flow_from_clientsecrets
from oauth2client.tools import run


import json
from tools import getPage

CLIENT_SECRETS = path.join(path.dirname(__file__), 'googledata.json')
MISSING_CLIENT_SECRETS_MESSAGE = """Please configure google credentials to %s file.""" % CLIENT_SECRETS


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
    flow = flow_from_clientsecrets(CLIENT_SECRETS,
           scope='https://www.googleapis.com/auth/latitude.all.best',
           message=MISSING_CLIENT_SECRETS_MESSAGE)
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
  try:
      return service.currentLocation().insert(body=body).execute()
  except HttpError:
      return None
