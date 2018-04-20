#!/usr/bin/python
import csv
import overpy
import zipfile
import re
import requests

from optparse import OptionParser

MAX_LINES_CSV = 3122

#-----------------------------------------------------------------------------
# Parse command line options
#-----------------------------------------------------------------------------
parser = OptionParser()
parser.add_option("-d", "--date", dest="date",
                  help="Only check those imports after the specified date (YYYYMMDD)")
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
if options.date != None:
   print("Filtering by date %s" % options.date)

if options.output != None:
   out_file = open(options.output, "wt")

with open('file_list.csv', 'rb') as csvfile:
    csvreader = csv.DictReader(csvfile)
    row_num = 0
    for row in csvreader:
        row_num = row_num + 1
        if (row_num <= MAX_LINES_CSV):
           if (row['uploader'] == options.uploader):
              date = row['date']
              place = row['place']

              if (options.place == None) or (place_regex.match(place)):
                 if (options.date == None) or (date > options.date):
                    osc_file_name = "linz_places/" + place + ".osc"
                    
                    # Find bounding box of nodes in OSC file
                    south=90.0
                    west=180.0
                    north=-90.0
                    east=0.0
                    addr_streets = set()
                    lat_lon = re.compile('node.*lat="(.*?)".*lon="(.*?)"')
                    addr_street = re.compile('"addr:street" v="(.*?)"')
                    if options.verbose:
                       print("Finding %s in zip file ..." % place)
                    with zipfile.ZipFile('linz_places.zip') as placesZip:
                      try:
                         with placesZip.open(osc_file_name) as osc_file:
                           for line in osc_file:
                              coords = lat_lon.search(str(line))
                              if coords:
                                 south = min(south, float(coords.group(1)))
                                 north = max(north, float(coords.group(1)))
                                 west = min(west, float(coords.group(2)))
                                 east = max(east, float(coords.group(2)))
                              else:
                                 street = addr_street.search(str(line))
                                 if street:
                                    #print (street.group(1))
                                    addr_streets.add(street.group(1))
                      except:
                         print("Error extracting %s from zip file" % osc_file_name)
                         continue
                    
                    print ("Place: %s,  Bound box: %f, %f, %f, %f, Imported on %s" % (place, south, west, north, east, date))
                    if options.output != None:
                       out_file.write("%s,%s,%s,%s,%s,%s\n" % (place,south,west,north,east,date))
                    
                    #-----------------------------------------------------------------------------
                    # Read highways within bounding box from OSM
                    #-----------------------------------------------------------------------------
                    south = south * 1.005
                    north = north * 0.995
                    east = east * 1.005
                    west = west * 0.995
                    
                    # fetch all ways
                    result = api.query("""
                        way(%f,%f,%f,%f) ["highway"];
                        out body;
                        """ % (south, west, north, east))
                    
                    highway_streets = set()
                    
                    for way in result.ways:
                        highway = way.tags.get("highway", "n/a")
                        if (highway != "footway") and (highway != "cycleway") and (highway != "service") and \
                           (highway != "motorway_link") and (highway != "path") and (highway != "steps"):
                           name = way.tags.get("name", "n/a")
                           highway_streets.add(name)
                           if options.verbose:
                              print("Name: %s \tHighway: %s" % (name, highway))
                    
                    #-----------------------------------------------------------------------------
                    # Find streets from addresses that don't exist
                    #-----------------------------------------------------------------------------
                    missing = 0
                    objects = ''
                    for street in addr_streets:
                       if street not in highway_streets:
                          print("Street: %s DOES NOT EXIST AS A HIGHWAY" % street)
                          if options.josm or (options.output != None):
                            # Get addr:street nodes for missing street and use the first to build the JOSM objects list
                            result = api.query("""
                               node(%f,%f,%f,%f) ["addr:street"="%s"];
                               out meta;
                               """ % (south, west, north, east,street))
                            if len(result.nodes) > 0:
                               objects = objects + 'n' + str(result.nodes[0].id) + ','
                               if options.output != None:
                                  out_file.write("   %s,%s\n" % (street, result.nodes[0].id))
                          missing=1
                          
                    print

                    if ((missing == 1) and (options.josm)):
                       print("Starting JOSM...")
                       print("http://127.0.0.1:8111/load_object?new_layer=true&objects=%s" % objects)
                       requests.get("http://127.0.0.1:8111/load_object?new_layer=true&objects=%s" % objects)
                       raw_input("Press enter to continue...")

if options.output != None:
   out_file.close() 
