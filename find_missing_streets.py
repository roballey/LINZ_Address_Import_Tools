#!/usr/bin/python
# NOTE: Known limitation: If a street appears in the OSC but was not imported and it doesn't exist as a highway in OSM
#       it will still be reported as a missing street
#       Known limitation: Streets that cross multiple places will be tested and reported for each place
import csv
import overpy
import zipfile
import re
import requests
import xml.etree.ElementTree as ET
import sys

from optparse import OptionParser

class bbox:
   south=90.0
   west=180.0
   north=-90.0
   east=0.0

   def update(self, lat, lon):
      self.south = min(self.south, lat)
      self.north = max(self.north, lat)
      self.east  = max(self.east, lon)
      self.west  = min(self.west, lon)

   def expand(self, factor):
      self.south *= (1.0 + factor)
      self.north *= (1.0 - factor)
      self.east  *= (1.0 + factor)
      self.west  *= (1.0 - factor)

   # Note: minimum is unit less
   def expand_at_least(self, factor, minimum):
      while (abs((self.north-self.south)*(self.west-self.east)) < minimum):
         self.expand(factor)

expansion_factor = 0.00001
min_area = 0.000001
seperator='( |-)'


#-----------------------------------------------------------------------------
# Parse command line options
#-----------------------------------------------------------------------------
parser = OptionParser()
parser.add_option("-a", "--after", dest="after",
                  help="Only check those imports after the specified date (YYYYMMDD)")
parser.add_option("-b", "--before", dest="before",
                  help="Only check those imports before the specified date (YYYYMMDD)")
parser.add_option("-o", "--output", dest="output",
                  help="Write output to a file for later processing")
parser.add_option("-p", "--place", dest="place",
                  help="Only check those imports that match the place name (regexp supproted)")
parser.add_option("-u", "--uploader", dest="uploader",
                  help="Specify uploader whose imports are to be checked", default="linz_robA")
parser.add_option("-j", "--josm",
                  action="store_true", dest="josm", default=False,
                  help="Use JOSM remote control interface to zoom to bounding box")
parser.add_option("-v", "--verbose",
                  action="store_true", dest="verbose", default=False,
                  help="Produce verbose output")

(options, args) = parser.parse_args()


#-----------------------------------------------------------------------------
# Initialisation
#-----------------------------------------------------------------------------
api = overpy.Overpass()

#-----------------------------------------------------------------------------
# Read data from address import tracking spreadsheet
#-----------------------------------------------------------------------------
print("Searching for locations imported by '%s'" % options.uploader)
if options.place != None:
   print("Filtering by place %s" % options.place)
   place_regex=re.compile(options.place)
if options.before != None:
   print("Filtering by before date %s" % options.before)
if options.after != None:
   print("Filtering by after date %s" % options.after)
sys.stdout.flush()

if options.output != None:
   out_file = open(options.output, "wt")

placesZip = zipfile.ZipFile('linz_places.zip')

with open('file_list.csv', 'rb') as csvfile:
    csvreader = csv.DictReader(csvfile)
    row_num = 0
    for row in csvreader:
        if row['place'] == 'TOTAL':
           break

        row_num = row_num + 1
        if (row['uploader'] == options.uploader):
           date = row['date']
           place = row['place']

           missing = 0
           objects = ''

           if (options.place == None) or (place_regex.match(place)):
              if ((options.after == None) or (date > options.after)) and \
                 ((options.before == None) or (date < options.before)):
                 osc_file_name = "linz_places/" + place + ".osc"

                 if options.output != None:
                    out_file.write("%s\n" % place)

                 addr_streets = set()
                 try:
                    with placesZip.open(osc_file_name) as osc_file:
                       if options.verbose:
                          print("Processing '%s'" % place)
                          sys.stdout.flush()

                       root = ET.parse(osc_file).getroot()
                       
                       streets = {}
                       
                       for node in root.iter('node'):
                          for tag in node.iter('tag'):
                             if tag.attrib.get('k') == 'addr:street':
                                street = tag.attrib.get('v')

                                if street not in streets:
                                  streets[street] = bbox()

                                streets[street].update(float(node.attrib.get('lat')), float(node.attrib.get('lon')))
                       
                       for name in streets:
                          if options.verbose:
                             print ("   Address Street '%s' [%f, %f, %f, %f]" % (name, streets[name].south, streets[name].west, streets[name].north, streets[name].east))
                             sys.stdout.flush()
                       
                          # Expand bounding box to try and ensure we find associated highway
                          streets[name].expand_at_least(expansion_factor, min_area)
                          # Download highway=* within bounding box
                          try:
                            result = api.query("""
                                way(%f,%f,%f,%f) ["highway"];
                                out body;
                                """ % (streets[name].south, streets[name].west, streets[name].north, streets[name].east))
                          except(KeyboardInterrupt):
                            print("\nQuitting")
                            quit()
                          except:
                            print("Error unable to query OSM - %s" % (sys.exc_info()[0]))
                            continue
                          
                          #if options.verbose:
                          #   print("Got %d ways from OSM" % len(result.ways))      

                          highway_streets = set()

                          for way in result.ways:
                              highway = way.tags.get("highway", "n/a")
                              if (highway != "footway") and (highway != "cycleway") and \
                                 (highway != "motorway_link") and (highway != "path") and (highway != "steps"):
                                 highway_name = way.tags.get("name", "n/a")

                                 if highway_name not in highway_streets:
                                    highway_streets.add(highway_name)
                                    if options.verbose:
                                       print("   Highway Name: %s \tType: %s" % (highway_name, highway)).encode('ascii', 'ignore')

                          #-----------------------------------------------------------------------------
                          # If name is not one of the highways downloads, street is missing
                          #-----------------------------------------------------------------------------

                          if '-' in name:
                            name_match = name.replace("-",seperator)
                            name_regex=re.compile(name_match)
                            found = False
                            for street in highway_streets:
                              if (name_regex.match(street)):
                                found = True
                                break
                           
                          elif name not in highway_streets:
                            found = False
                          else:
                            found = True

                          if not found:
                                missing += 1

                                print("*** Address Street: %s DOES NOT HAVE A HIGHWAY" % name)
                                sys.stdout.flush()

                                if options.josm or (options.output != None):
                                   # Get addr:street nodes for missing street and use the first to build the JOSM objects list
                                   result = api.query("""
                                      node(%f,%f,%f,%f) ["addr:street"="%s"];
                                      out meta;
                                      """ % (streets[name].south, streets[name].west, streets[name].north, streets[name].east, name))

                                   if len(result.nodes) > 0:
                                      objects = objects + 'n' + str(result.nodes[0].id) + ','
                                      if options.output != None:
                                         out_file.write("   %s,%s\n" % (name, result.nodes[0].id))

                          if options.verbose:
                             print ('')
                          if options.output != None:
                             out_file.flush()



                 except(KeyboardInterrupt):
                    print("\nQuitting")
                    quit()
                 except:
                    print("Error reading %s from zip file - %s" % (osc_file_name, sys.exc_info()[0]))
                    continue
                 
                 #-----------------------------------------------------------------------------
                 # Read highways within bounding box from OSM
                 #-----------------------------------------------------------------------------
                 
           if missing > 0:
              print("Place '%s' has %d missing highways %s" % (place , missing, objects))
              sys.stdout.flush()

              if (options.josm):
                 print("Starting JOSM...")
                 print("http://127.0.0.1:8111/load_object?new_layer=true&objects=%s" % objects)
                 sys.stdout.flush()

                 requests.get("http://127.0.0.1:8111/load_object?new_layer=true&objects=%s" % objects)

                 raw_input("Press enter to continue...")
                 sys.stdout.flush()


if options.output != None:
   out_file.close() 
