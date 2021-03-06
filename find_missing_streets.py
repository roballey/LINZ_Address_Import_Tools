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

import argparse

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

total_missing = 0
total_places = 0
total_queries = 0
expansion_factor = 0.00005
seperator_alt='( |-)'
saint_alt='(St |Saint )'


#-----------------------------------------------------------------------------
# Parse command line arguments
#-----------------------------------------------------------------------------
parser = argparse.ArgumentParser()
parser.add_argument("-a", "--after", dest="after",
                  help="Only check those imports after the specified date (YYYYMMDD)")
parser.add_argument("-b", "--before", dest="before",
                  help="Only check those imports before the specified date (YYYYMMDD)")
parser.add_argument("-o", "--output", dest="output",
                  help="Write output to a file for later processing")
parser.add_argument("-p", "--place", dest="place",
                  help="Only check those imports that match the place name (regexp supported)")
parser.add_argument("-u", "--uploader", dest="uploader",
                  help="Specify uploader whose imports are to be checked", default="linz_robA")
parser.add_argument("-j", "--josm",
                  action="store_true", dest="josm", default=False,
                  help="Use JOSM remote control interface to zoom to bounding box")
parser.add_argument("-s", "--saint",
                  action="store_true", dest="saint", default=False,
                  help="Match 'St' or 'Saint' is OSM highway name for address street names using 'St'")
parser.add_argument("-v", "--verbose",
                  action="store_true", dest="verbose", default=False,
                  help="Produce verbose output")

args = parser.parse_args()


#-----------------------------------------------------------------------------
# Initialisation
#-----------------------------------------------------------------------------
api = overpy.Overpass()

#-----------------------------------------------------------------------------
# Read data from address import tracking spreadsheet
#-----------------------------------------------------------------------------
print("Searching for locations imported by '%s'" % args.uploader)
if args.place != None:
   print("Filtering by place %s" % args.place)
   place_regex=re.compile(args.place)
if args.before != None:
   print("Filtering by before date %s" % args.before)
if args.after != None:
   print("Filtering by after date %s" % args.after)
sys.stdout.flush()

if args.output != None:
   out_file = open(args.output, "wt")

placesZip = zipfile.ZipFile('linz_places.zip')

with open('file_list.csv', 'rb') as csvfile:
    csvreader = csv.DictReader(csvfile)
    row_num = 0
    for row in csvreader:
        if row['place'] == 'TOTAL':
           break

        row_num = row_num + 1

        # Process each place imported by the specified uploader
        if (row['uploader'] == args.uploader):
           date = row['date']
           place = row['place']

           missing = 0
           objects = ''

           if (args.place == None) or (place_regex.match(place)):
              if ((args.after == None) or (date > args.after)) and \
                 ((args.before == None) or (date < args.before)):
                 osc_file_name = "linz_places/" + place + ".osc"

                 if args.output != None:
                    out_file.write("%s\n" % place)

                 addr_streets = set()
                 try:
                    with placesZip.open(osc_file_name) as osc_file:
                       if args.verbose:
                          print("Finding streets for '%s'" % place)
                          sys.stdout.flush()

                       total_places += 1
                       root = ET.parse(osc_file).getroot()

                       place_bounds = bbox()
                       
                       address_streets = {}
                       
                       for node in root.iter('node'):
                          for tag in node.iter('tag'):
                             if tag.attrib.get('k') == 'addr:street':
                                street_name = tag.attrib.get('v')

                                # Add street to dictionary of unique street names
                                if street_name not in address_streets:
                                  address_streets[street_name] = bbox()

                                # Update the bounding box for this current street
                                address_streets[street_name].update(float(node.attrib.get('lat')), float(node.attrib.get('lon')))

                                place_bounds.update(float(node.attrib.get('lat')), float(node.attrib.get('lon')))
                      
                       # Process each street for a place
                       for address_street in address_streets:
                          if args.verbose:
                             print ("   Address Street '%s' [%f, %f, %f, %f]" % (address_street, address_streets[address_street].south, address_streets[address_street].west, address_streets[address_street].north, address_streets[address_street].east))
                             sys.stdout.flush()
                     
                    # Expand the bounding box size to attempt to pick up nearby highways
                    place_bounds.expand(expansion_factor)

                    # Download all highway=* for the place
                    if args.verbose:
                       print("Downloading highways from OSM for place '%s' inside bounding box [%f, %f, %f, %f]" % (place, place_bounds.south, place_bounds.west, place_bounds.north, place_bounds.east))
                       sys.stdout.flush()

                    try:
                      result = api.query("""
                          way(%f,%f,%f,%f) ["highway"];
                          out body;
                          """ % (place_bounds.south, place_bounds.west, place_bounds.north, place_bounds.east))
                      total_queries += 1;
                    except(KeyboardInterrupt):
                      print("\nQuitting during highway download")
                      sys.exit()
                    except:
                      print("Error unable to query OSM - %s" % (sys.exc_info()[0]))
                      continue
                    
                    if args.verbose:
                       print("Got %d ways from OSM" % len(result.ways))      

                    # Build a list of unique highway names, ignoring highways that aren't streets
                    highway_names = set()
                    for way in result.ways:
                        highway = way.tags.get("highway", "n/a")
                        if (highway != "footway") and (highway != "cycleway") and \
                           (highway != "motorway_link") and (highway != "path") and (highway != "steps"):
                            highway_name = way.tags.get("name", "n/a")

                            if highway_name not in highway_names:
                               highway_names.add(highway_name)
                               if args.verbose:
                                   print("   Highway Name: %s \tType: %s" % (highway_name, highway)).encode('ascii', 'ignore')

                    for address_street in address_streets:

                       found = False
                       if (args.saint and ('St ' in address_street)):
                         if args.verbose:
                            print("   Address street name '%s' may also match highway name 'Saint...'" % address_street)
                         name_match = address_street.replace("St ",saint_alt)
                         name_regex=re.compile(name_match)
                         for highway_name in highway_names:
                           if (name_regex.match(highway_name)):
                             found = True
                             if args.verbose:
                                print("      Address street name '%s' matched highway name '%s'" % (address_street, highway_name))
                             break

                       # If address street name contains '-' seperator also match against other seperators
                       elif '-' in address_street:
                         name_match = address_street.replace("-",seperator_alt)
                         name_regex=re.compile(name_match)
                         for highway_name in highway_names:
                           if (name_regex.match(highway_name)):
                             found = True
                             break
                        
                       elif address_street in highway_names:
                         found = True

                       if not found:
                          missing += 1
                          total_missing += 1
                          print("*** Addresses imported for Street: '%s' which does not have matching highway in OSM" % address_street)
                          sys.stdout.flush()

                          if args.josm or (args.output != None):
                             # Get addr:street nodes for missing street and use the first to build the JOSM objects list
                             try:
                                result = api.query("""
                                   node(%f,%f,%f,%f) ["addr:street"="%s"];
                                   out meta;
                                   """ % (address_streets[address_street].south, address_streets[address_street].west, address_streets[address_street].north, address_streets[address_street].east, address_street))
                                total_queries += 1;

                                if len(result.nodes) > 0:
                                   objects = objects + 'n' + str(result.nodes[0].id) + ','
                                   if args.output != None:
                                      out_file.write("   %s,%s\n" % (address_street, result.nodes[0].id))
                                      out_file.flush()
                                # If we get 0 records then address is marked as imported but can't be found in OSM
                                else:
                                   print("    *** Unable to find address nodes for Street: '%s' in OSM" % address_street)
                             except(KeyboardInterrupt):
                               print("\nQuitting during address download")
                               sys.exit()
                             except:
                               print("Error unable to query OSM - %s" % (sys.exc_info()[0]))
                               continue

                 except(KeyboardInterrupt):
                   print("\nQuitting in zip processing")
                   sys.exit()
                 except(SystemExit):
                    print("\nExit in zip processing")
                    sys.exit()
                 except:
                    print("Error reading %s from zip file - %s" % (osc_file_name, sys.exc_info()[0]))
                    continue
                 

           if missing > 0:
              print("Place '%s' has %d missing highways" % (place , missing))
              sys.stdout.flush()

              if (args.josm):
                 print("Starting JOSM...")
                 print("http://127.0.0.1:8111/load_object?new_layer=true&objects=%s" % objects)
                 sys.stdout.flush()

                 requests.get("http://127.0.0.1:8111/load_object?new_layer=true&objects=%s" % objects)

                 raw_input("Press enter to continue...")
                 sys.stdout.flush()


if args.output != None:
   out_file.close() 

print("Total of %d missing highways in %d places" % (total_missing, total_places))
print("Made a total of %d overpass queries" % total_queries)
