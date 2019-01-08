#!/usr/bin/python
import csv
import zipfile
import re
import sys
import overpy

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


from optparse import OptionParser
# WIP find addresses that have been imported that do not have a corresponding
#     place in OSM (i.e. no node with place=* and name=<NAME>, where <NAME>
#     comes from addr=hamlet|... tag value in the OSC file)
#-----------------------------------------------------------------------------
# Parse command line options
#-----------------------------------------------------------------------------
parser = OptionParser()
parser.add_option("-a", "--above", dest="above", type="float", 
                  help="Specify latitude above which to find places to import")
parser.add_option("-b", "--below", dest="below", type="float", 
                  help="Specify latitude below which to find places to import")
parser.add_option("-f", "--listfile",
                  action="store", dest="list_filename", default='file_list.csv',
                  help="Name of CSV file containing the status of the import")
parser.add_option("-p", "--place", dest="place",
                  help="Only check those imports that match the place name (regexp supported)")
parser.add_option("-l", "--left", dest="left", type="float", 
                  help="Specify longitude left of which to find places to import")
parser.add_option("-m", "--mismatch",
                  action="store_true", dest="mismatch", default=False,
                  help="Report where the place type in OSM does not match that imported from OSC files")
parser.add_option("-r", "--right", dest="right", type="float", 
                  help="Specify longitude right of which to find places to import")
parser.add_option("-u", "--user",
                  action="store", dest="user", default='linz_robA',
                  help="Name of OSM user whose imports are to be checked")
parser.add_option("-v", "--verbose",
                  action="store_true", dest="verbose", default=False,
                  help="Produce verbose output")
parser.add_option("-z", "--zipfile",
                  action="store", dest="zip_filename", default='linz_places.zip',
                  help="Name of zip file containing the OSC files to be imported")
(options, args) = parser.parse_args()

#-----------------------------------------------------------------------------
# Display start message
#-----------------------------------------------------------------------------
print("Searching for address imports that don't have a corresponding place in OSM")
if (options.above != None):
   print("   above (north of) %f" % options.above)
if (options.below != None):
   print("   below (south of) %f" % options.below)
if (options.left != None):
   print("   left (west) of %f" % options.left)
if (options.right != None):
   print("   right (east) of %f" % options.right)
if options.place != None:
   print("   filtering by place='%s'" % options.place)
   place_regex=re.compile(options.place)
print("")
sys.stdout.flush()

lat_lon = re.compile('node.*lat="(.*?)".*lon="(.*?)"')
# TODO: Do the OSC files only encode addresses as hamlet or suburb?
place_type_re = re.compile('tag.*"addr:(hamlet|suburb)" v="(.*?)"')
api = overpy.Overpass()
not_in_osm = 0
#-----------------------------------------------------------------------------
# Read data from address import tracking spreadsheet
#-----------------------------------------------------------------------------
with open(options.list_filename, 'rt') as csvfile:
    csvreader = csv.DictReader(csvfile)

    row_num = 0
    total_places=0
    total_addresses=0
    checked_places = 0
    checked_addresses = 0
    matching_places = 0
    matching_addresses = 0
    mismatched_types = 0

    placesZip = zipfile.ZipFile(options.zip_filename)

    for row in csvreader:

        # Stop processing CSV file as soon as we get to row starting with "TOTAL"
        if row['place'] == 'TOTAL':
           break

        addresses = int(row['num_addresses'])

        row_num = row_num + 1
        total_places += 1
        total_addresses += addresses

        place_imported=False

        if (row['uploader'] == options.user):
           checked_places += 1
           place = row['place']
           checked_addresses += addresses
           if options.verbose:
              print("Checking %s" % place)
              sys.stdout.flush()

           osc_file_name = "linz_places/" + place + ".osc"
          
           if ((options.above != None) or 
               (options.below != None) or 
               (options.left != None)  or 
               (options.right != None) or
               (options.place != None)) :

             try:
               with placesZip.open(osc_file_name) as osc_file:
                 for line in osc_file:
                    coords = lat_lon.search(str(line))
                    if coords and \
                       (((options.above == None) or (float(coords.group(1)) > options.above)) and
                        ((options.below == None) or (float(coords.group(1)) < options.below)) and
                        ((options.left == None)  or (float(coords.group(2)) < options.left)) and
                        ((options.right == None) or (float(coords.group(2)) > options.right))):

                      if (options.place == None) or (place_regex.match(place)):

                        place_imported=True

                      break
             except:
               print("***ERROR occurred extracting %s" % osc_file_name)

           else:
             place_imported=True

           if place_imported:
             matching_places += 1
             matching_addresses += addresses
             if options.verbose:
               print ("Place: %s - imported" % (place))
             place_bbox = bbox()
             place_type_found = False
             place_type = "UNKNOWN"

             # Now check if there is a corresponding place in OSM
             # TODO: Don't re-open zip file?
             try:
               osc_file = placesZip.open(osc_file_name)
             except:
               print("***ERROR occurred extracting %s - %s" % (osc_file_name, sys.exc_info()[0]))

             for line in osc_file:
                coords = lat_lon.search(str(line))
                # Determine bounding box of imported address nodes
                if (coords):
                  place_bbox.update(float(coords.group(1)), float(coords.group(2)))
                elif (not place_type_found):
                  place_type = place_type_re.search(str(line))
                  if (place_type):
                    imported_place_type=place_type.group(1)
                    imported_place_name=place_type.group(2)
                    if options.verbose:
                      print("   Place: %s Type is %s" % (place, place_type.group(1)))
                    place_type_found = True

             if (not place_type_found):
               imported_place_type="UNKNOWN"
               imported_place_name="UNKNOWN"
               print("*** Place: %s Type is UNKNOWN" % (place))

             # Query OSM for place in OSM (i.e. node with place=<place_type> and name=<place>)
             result = api.query("""
             node(%f,%f,%f,%f) ["place"];
             out body;
             """ % (place_bbox.south, place_bbox.west, place_bbox.north, place_bbox.east))

             found_in_osm = False
             for node in result.nodes:
               if (node.tags.get("name", "UNKNOWN") == imported_place_name):
                 found_in_osm = True

                 # TODO: This logic needs work since places from OSM use more values than the OSC files 
                 if (options.mismatch and (node.tags.get("place", "UNKNOWN") != imported_place_type)):
                   mismatched_types += 1
                   print("'%s' uses type '%s' for address nodes but type '%s' on place node" % (imported_place_name, imported_place_type, node.tags.get("place", "UNKNOWN")))
                 if options.verbose:
                   print("   OSM place %s" % node.tags.get("place", "UNKNOWN"))
                   # Encode is required for Windows 
                   print("   OSM name %s" % node.tags.get("name", "UNKNOWN").encode('ascii', 'ignore'))
                 break

             if (not found_in_osm):
               not_in_osm += 1
               print("%s '%s' does not have a place node in OSM" % (imported_place_type, imported_place_name))
               sys.stdout.flush()



    print("\nCSV file contains a total of %d places with %d addresses" % (total_places, total_addresses))
    print("Checked %d places imported by '%s' with %d addresses" % (checked_places, options.user, checked_addresses))
    print("Found %d places imported by '%s' with %d addresses match restrictions" % (matching_places, options.user, matching_addresses))
    print("Found %d imported places that don't have a corresponding place node in OSM" % (not_in_osm))
    if options.mismatch:
      print("Found %d imported places that mismatched types" % (mismatched_types))

