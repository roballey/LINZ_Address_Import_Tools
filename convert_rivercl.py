#!/usr/bin/python
#-----------------------------------------------------------------------------
# Read river centre line data from a LINZ CSV file and convert
# to OSM format optionally restricting conversion to those rivers
# that have at least one point within the specified bounds (from an OSM file)
#-----------------------------------------------------------------------------
import csv
import re
import sys
from pyproj import Proj, transform

# Convert river co-ords from NZTM 2000 (see http://epsg.io/2193)
inProj = Proj(init='epsg:2193')

# Convert river co-ords to WGS84 (see http://epsg.io/4326)
outProj = Proj(init='epsg:4326')

from optparse import OptionParser

class OSMId:

   def __init__(self):
     self.number = -30000

   def Generate(self):
     self.number = self.number - 1
     return self.number

class bbox:
   south=90.0
   west=180.0
   north=-90.0
   east=0.0

   def update(self, lat, lon):
      #print("Update %.3f %.3f"%(lat,lon))
      self.south = min(self.south, lat)
      self.north = max(self.north, lat)
      self.east  = max(self.east, lon)
      self.west  = min(self.west, lon)

   def contains(self, lat, lon):
      #print("Is %.3f inside %.3f\n" % (lat, self.south))
      if ((lat >= self.south) and
          (lat <= self.north) and
          (lon >= self.west) and
          (lon <= self.east)):
         #print("INSIDE: %.3f %.3f" % (lat, lon))
         return True
      else:
         return False


class point:
   def __init__(self,lat,lon):
      self.lat=lat
      self.lon=lon

#-----------------------------------------------------------------------------
# Parse command line options
#-----------------------------------------------------------------------------
parser = OptionParser()
parser.add_option("-b", "--boundsfile",
                  action="store", dest="bounds_filename",
                  help="Name of the input OSM file containing bounds of data to be converted (optional)")
parser.add_option("-f", "--inputfile",
                  action="store", dest="input_filename", default='nz-river-centrelines-topo-150k.csv',
                  help="Name of the input CSV file containing data to be converted")
(options, args) = parser.parse_args()

osmId = OSMId()

#-----------------------------------------------------------------------------
# Parse bounds file
#-----------------------------------------------------------------------------
if options.bounds_filename != None:
  bounds = bbox()
  with open(options.bounds_filename, 'rt') as boundsfile:
    for line in boundsfile:
      m = re.search("node.*lat='(.*)' lon='(.*)'", line)
      if m != None:
        bounds.update(float(m.group(1)), float(m.group(2)))
  #print bounds.north, bounds.south, bounds.east, bounds.west

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
        nodes = []
        inBounds = False

        m = re.match("LINESTRING \((.*)\)", row['WKT'])

        # Parse node co-ordinates and convert
        for coord in m.group(1).split(','):
            (x, y) = coord.split(' ')
            lon,lat = transform(inProj,outProj,x,y)
            nodes.append(point(lat,lon))
            if ((options.bounds_filename != None) and (bounds.contains(lat,lon))):
               inBounds = True

        # Write each co-ordinate as an OSM node
        if ((options.bounds_filename == None) or (inBounds == True)):
           for node in nodes:
              print("  <node id='%d' action='modify' lat='%s' lon='%s' />" % ( osmId.Generate(), node.lat, node.lon))
              nodesIds.append(osmId.number)

           # Write the waterway as an OSM way using each of the nodes
           print("  <way id='%d' action='modify'>" % osmId.Generate())
           for nodeId in nodesIds:
               print("    <nd ref='%d' />" % nodeId)
           # TODO: Is there anyway to automatically determine if the waterway is a river, stream or creek etc.?
           print("    <tag k='waterway' v='stream' />")
           print("  </way>")

print("</osm>")
