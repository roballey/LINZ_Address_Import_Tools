#!/usr/bin/python
import csv
import zipfile
import re
import sys

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
parser.add_option("-l", "--left", dest="left", type="float", 
                  help="Specify longitude left of which to find places to import")
parser.add_option("-r", "--right", dest="right", type="float", 
                  help="Specify longitude right of which to find places to import")
parser.add_option("-v", "--verbose",
                  action="store_true", dest="verbose", default=False,
                  help="Produce verbose output")
parser.add_option("-z", "--zipfile",
                  action="store", dest="zip_filename", default='linz_places.zip',
                  help="Name of zip file containing the OSC files to be imported")
(options, args) = parser.parse_args()
# TODO: Allow filtering by place

#-----------------------------------------------------------------------------
# Display start message
#-----------------------------------------------------------------------------
print("Searching for locations still to to be imported")
if (options.above != None):
   print("   above (north of) %f" % options.above)
if (options.below != None):
   print("   below (south of) %f" % options.below)
if (options.left != None):
   print("   left (west) of %f" % options.left)
if (options.right != None):
   print("   right (east) of %f" % options.right)
print("")

lat_lon = re.compile('node.*lat="(.*?)".*lon="(.*?)"')
place_type_re = re.compile('tag.*"addr:(hamlet|suburb)" v=".*?"')
uploader = "linz_robA"   # TODO: Get this from command line
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

        if (row['uploader'] == uploader):
           checked_places += 1
           place = row['place']
           checked_addresses += addresses
           if options.verbose:
              print("Checking %s" % place)

           osc_file_name = "linz_places/" + place + ".osc"
          
           if ((options.above != None) or 
               (options.below != None) or 
               (options.left != None)  or 
               (options.right != None)) :

             try:
               with placesZip.open(osc_file_name) as osc_file:
                 for line in osc_file:
                    coords = lat_lon.search(str(line))
                    if coords and \
                       (((options.above == None) or (float(coords.group(1)) > options.above)) and
                        ((options.below == None) or (float(coords.group(1)) < options.below)) and
                        ((options.left == None)  or (float(coords.group(2)) < options.left)) and
                        ((options.right == None) or (float(coords.group(2)) > options.right))):

                      place_imported=True

                      break
             except:
               print("***ERROR occurred extracting %s" % osc_file_name)

           else:
             place_imported=True

           if place_imported:
             matching_places += 1
             matching_addresses += addresses
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
                    print("   Place: %s Type is %s" % (place, place_type.group(1)))
                    place_type_found = True

             if (not place_type_found):
               print("*** Place: %s Type is UNKNOWN" % (place))

             # TODO: Query OSM for place in OSM (i.e. node with place=<place_type> and name=<place>)



    print("\nCSV file contains a total of %d places with %d addresses" % (total_places, total_addresses))
    print("Checked %d places imported by '%s' with %d addresses" % (checked_places, uploader, checked_addresses))
    print("Found %d places imported by '%s' with %d addresses match restrictions" % (matching_places, uploader, matching_addresses))
