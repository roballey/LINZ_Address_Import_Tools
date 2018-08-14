#!/usr/bin/python
import csv
import re
import sys

from optparse import OptionParser

class OSMId:

   def __init__(self):
     self.number = -30000

   def New(self):
     self.number = self.number - 1
     return self.number

#-----------------------------------------------------------------------------
# Parse command line options
#-----------------------------------------------------------------------------
parser = OptionParser()
parser.add_option("-f", "--inputfile",
                  action="store", dest="input_filename", default='missing_to_be_added_to_osm.csv',
                  help="Name of the input CSV file containing roads to be converted")
(options, args) = parser.parse_args()

#-----------------------------------------------------------------------------
# Display start message
#-----------------------------------------------------------------------------
print("Converting LINZ roads CSV file (extract)...")
print("")
sys.stdout.flush()

osmId = OSMId()

print("<?xml version='1.0' encoding='UTF-8'?>")
print("<osm version='0.6' generator='JOSM'>")

#-----------------------------------------------------------------------------
# Read data from address import tracking spreadsheet
# TODO: Could re-write to specify street name on command line and extract that
#       street directly from original OSM CSV file
#-----------------------------------------------------------------------------
with open(options.input_filename, 'rt') as csvfile:
    csvreader = csv.DictReader(csvfile)

    for row in csvreader:

        nodesIds = [] 
        m = re.match("MULTILINESTRING \(\((.*)\)\)", row['WKT'])

        # Write each co-ordinate as an OSM node
        for coord in m.group(1).split(','):
            (lon, lat) = coord.split(' ')
            print("  <node id='%d' action='modify' lat='%s' lon='%s' />" % ( osmId.New(), lat, lon))
            nodesIds.append(osmId.number)

        # Write the street as an OSM way using each of the nodes
        print("  <way id='%d' action='modify'>" % osmId.New())
        for nodeId in nodesIds:
            print("    <nd ref='%d' />" % nodeId)
        print("    <tag k='highway' v='unclassified' />")
        print("    <tag k='name' v='%s' />" % (row['full_road_name']))
        print("  </way>")

print("</osm>")
