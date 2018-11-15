#!/usr/bin/python
#-----------------------------------------------------------------------------
# Read road data from a LINZ roads-subsections-addressing.csv file and convert
# to OSM format optionally restricting conversion to those roads
# that have at least one point within the specified bounds (from an OSM file)
#-----------------------------------------------------------------------------
import csv
import re
import sys

from optparse import OptionParser

class OSMId:

   def __init__(self):
     self.number = -30000

   def generate(self):
     self.number = self.number - 1
     return self.number

class Point:
   def __init__(self,lat,lon):
      self.lat=lat
      self.lon=lon

class Bbox:
   def __init__(self,north,south,east,west):
      self.north = north
      self.south = south
      self.east = east
      self.west = west

class Polygon:
   bbox = Bbox(-90.0, 90.0, 0.0, 180.0)

   def update(self, point):
      self.bbox.south = min(self.bbox.south, point.lat)
      self.bbox.north = max(self.bbox.north, point.lat)
      self.bbox.east  = max(self.bbox.east, point.lon)
      self.bbox.west  = min(self.bbox.west, point.lon)
      # TODO: also save point for when we extend contains method

   def bbox_contains(self, lat, lon):
      #print("Check lat %.3f lon %.3f" % (lat, lon));
      if ((lat >= self.bbox.south) and
          (lat <= self.bbox.north) and
          (lon >= self.bbox.west) and
          (lon <= self.bbox.east)):
         return True
      else:
         return False

   # TODO: After determining that the polygons bbox contains the point should determine
   #       whether the point actually lies within the polygon
   def contains(self, lat, lon):
      return self.bbox_contains(lat, lon)


#-----------------------------------------------------------------------------
# Parse command line options
#-----------------------------------------------------------------------------
parser = OptionParser()
parser.add_option("-b", "--boundsfile",
                  action="store", dest="bounds_filename",
                  help="Name of the input OSM file containing bounds of data to be converted (optional)")
parser.add_option("-f", "--inputfile",
                  action="store", dest="input_filename", default='missing_to_be_added_to_osm.csv',
                  help="Name of the input CSV file containing roads to be converted")
(options, args) = parser.parse_args()

osmId = OSMId()
boundsNode = re.compile("node.*lat='(.*)' lon='(.*)'")
roadNodes = re.compile("MULTILINESTRING \(\((.*)\)\)")

#-----------------------------------------------------------------------------
# Parse bounds file
#-----------------------------------------------------------------------------
if options.bounds_filename != None:
  bounds = Polygon()
  with open(options.bounds_filename, 'rt') as boundsfile:
    for line in boundsfile:
      nodeCoords = boundsNode.search(line)
      if nodeCoords != None:
        bounds.update(Point(lat=float(nodeCoords.group(1)), lon=float(nodeCoords.group(2))))

#-----------------------------------------------------------------------------
# Output OSM file header
#-----------------------------------------------------------------------------
print("<?xml version='1.0' encoding='UTF-8'?>")
print("<osm version='0.6' generator='JOSM'>")

#-----------------------------------------------------------------------------
# Read road data from a LINZ CSV file and convert to OSM format
#-----------------------------------------------------------------------------
with open(options.input_filename, 'rt') as csvfile:
    csvreader = csv.DictReader(csvfile)

    for row in csvreader:

        nodesIds = [] 
        nodes = []
        inBounds = False

        m = roadNodes.match(row['WKT'])

        # Parse node co-ordinates
        for coord in m.group(1).split(','):
            (lon, lat) = coord.split(' ')
            nodes.append(Point(lat,lon))
            if ((options.bounds_filename != None) and (bounds.contains(float(lat),float(lon)))):
               inBounds = True

        #print("Bbox N%.3f E%.3f" % (bounds.bbox.north, bounds.bbox.east))
        # Write each co-ordinate as an OSM node
        if ((options.bounds_filename == None) or (inBounds == True)):
           for node in nodes:
              print("  <node id='%d' action='modify' lat='%s' lon='%s' />" % ( osmId.generate(), node.lat, node.lon))
              nodesIds.append(osmId.number)

           # Write the street as an OSM way using each of the nodes
           print("  <way id='%d' action='modify'>" % osmId.generate())
           for nodeId in nodesIds:
               print("    <nd ref='%d' />" % nodeId)
           print("    <tag k='highway' v='unclassified' />")
           print("    <tag k='name' v='%s' />" % (row['full_road_name'].replace("'","&apos;").replace("&","&amp;")))
           print("  </way>")

print("</osm>")
