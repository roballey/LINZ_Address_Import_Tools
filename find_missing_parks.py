#! /bin/python

import csv
import xml.etree.ElementTree as ET

import codecs
import sys
import time
from geopy.geocoders import Nominatim

# Enable unicode output to StdOut
UTF8Writer = codecs.getwriter('utf8')
sys.stdout = UTF8Writer(sys.stdout)

geolocator = Nominatim(user_agent="find_missing_parks",country_bias="nz",timeout=20)

# Extract names of ways and relations in Auckland parks extracted from OSM
print("Extracting parks names in OSM...")
tree = ET.parse('Auckland_Parks.osm')
root = tree.getroot()

osm_parks=[]

osm = ET.Element('osm')
osm.set('version',"0.6")
osm.set('generator',"find_missing_parks")

for child in root:
    if child.tag == "way" or child.tag == "relation":
        for tag in child.findall('tag'):
            if tag.attrib['k']=='name':
                osm_parks.append(tag.attrib['v'])


with open("AC/ParksAndReserves.csv", 'rt') as csvfile:
    csvreader = csv.DictReader(csvfile)

    count = 1
    for row in csvreader:
        #print("%s"%row['Description'])
        if row['Description'] in osm_parks:
            print("Found park '%s' in OSM"%row['Description'])
        else:
            print("*** Park '%s' at '%s' not in OSM"%(row['Description'],row['Address']))
            location = geolocator.geocode(row['Address']+", "+row["Postal Code"])
            if location is not None:

                node = ET.SubElement(osm, 'node')
                node.set('id',str(-1*count))
                node.set('lat',str(location.latitude))
                node.set('lon',str(location.longitude))
                tag = ET.SubElement(node, 'tag')
                tag.set('k','description')
                tag.set('v',row['Description'])

                sys.stdout.flush()
                time.sleep(1)
                count += 1
            else:
                print("   - Can't find address")

tree = ET.ElementTree(osm)
tree.write("missing_parks.osm")

