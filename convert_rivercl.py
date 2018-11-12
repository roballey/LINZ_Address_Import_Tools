#!/usr/bin/python
#-----------------------------------------------------------------------------
# Read river centre line data from a LINZ CSV file and convert
# to OSM format
#-----------------------------------------------------------------------------
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
                  action="store", dest="input_filename", default='nz-river-centrelines-topo-150k.csv',
                  help="Name of the input CSV file containing data to be converted")
(options, args) = parser.parse_args()

osmId = OSMId()

#-----------------------------------------------------------------------------
# Output OSM file header
#-----------------------------------------------------------------------------
print("<?xml version='1.0' encoding='UTF-8'?>")
print("<osm version='0.6' generator='JOSM'>")

#-----------------------------------------------------------------------------
# Read data from a LINZ CSV file and convert to OSM format
#-----------------------------------------------------------------------------
with open(options.input_filename, 'rt') as csvfile:
    csvreader = csv.DictReader(csvfile)

    for row in csvreader:

        nodesIds = [] 

        m = re.match("LINESTRING \((.*)\)", row['WKT'])

        # Write each co-ordinate as an OSM node
        for coord in m.group(1).split(','):
            (lon, lat) = coord.split(' ')
            print("  <node id='%d' action='modify' lat='%s' lon='%s' />" % ( osmId.New(), lat, lon))
            nodesIds.append(osmId.number)

        # Write the street as an OSM way using each of the nodes
        print("  <way id='%d' action='modify'>" % osmId.New())
        for nodeId in nodesIds:
            print("    <nd ref='%d' />" % nodeId)
        print("    <tag k='waterway' v='stream' />")
        print("  </way>")

print("</osm>")
