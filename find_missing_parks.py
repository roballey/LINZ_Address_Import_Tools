#! /bin/python
# Find Auckland parks that are missing from OSM
# Input files: AC/ParksAndReserves.csv - List of all Auckland Parks
#              Auckland_Parks.osm - Extract of OSM data tagged leisure=park within the Auckland region

# Note: Modified to retry on timeout exceptions, needs testing
#       Re-base on master after pushing latest mods from home

import csv
import xml.etree.ElementTree as ET

import codecs
import sys
import time
from geopy.geocoders import Nominatim # TODO: Consider using Photon instead

from tenacity import retry

# Get co-ordinates for an address, retrying after a 5s pause if there is a timeout
@retry(wait=wait_fixed(5), retry_if_exception_type(geopy.exc.GeocoderTimeOut))
def geocode_with_retry(address):
   return geolocator.geocode(address)

# Enable unicode output to StdOut
UTF8Writer = codecs.getwriter('utf8')
sys.stdout = UTF8Writer(sys.stdout)

geolocator = Nominatim(user_agent="find_missing_parks",country_bias="nz")

# Extract names of ways and relations in Auckland parks extracted from OSM
print("Extracting parks names in OSM...")
tree = ET.parse('Auckland_Parks.osm')
root = tree.getroot()

osm_parks=[]

osm = ET.Element('osm')
osm.set('version',"0.6")
osm.set('generator',"find_missing_parks")

# Build a list of all parks in OSM
for child in root:
    if child.tag == "way" or child.tag == "relation":
        for tag in child.findall('tag'):
            if tag.attrib['k']=='name':
                osm_parks.append(tag.attrib['v'])


# Search list of Auckland parks for parks not in OSM
with open("AC/ParksAndReserves.csv", 'rt') as csvfile:
    csvreader = csv.DictReader(csvfile)

    count = 1
    for row in csvreader:
        if row['Description'] in osm_parks:
            print("Found park '%s' in OSM"%row['Description'])
        else:
            print("*** Park '%s' at '%s' not in OSM"%(row['Description'],row['Address']))
            # TODO: Use viewbox=((lat,lng),(lat,lng)) and bounded=True to limit resutls to Auckland?
            location = geocode_with_retry(row['Address']+", "+row["Postal Code"])
            if location is not None:
                print("   - At %s,%s"%(location.latitude,location.longitude))

                node = ET.SubElement(osm, 'node')
                node.set('id',str(-1*count))
                node.set('lat',str(location.latitude))
                node.set('lon',str(location.longitude))
                tag = ET.SubElement(node, 'tag')
                tag.set('k','description')
                tag.set('v',row['Description'])

                sys.stdout.flush()
                time.sleep(2)
                count += 1
                if (count > 2):
                    ET.dump(osm)
                    tree = ET.ElementTree(osm)
                    tree.write("missing_parks.osm")
                    break
            else:
                print("   - Can't find address")

