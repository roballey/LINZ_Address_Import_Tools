#!/usr/bin/python
import csv
import zipfile
import re

from optparse import OptionParser

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
parser.add_option("-m", "--more", dest="more", type="int", 
                  help="Only report places with more than this many addresses")
parser.add_option("-r", "--right", dest="right", type="float", 
                  help="Specify longitude right of which to find places to import")
parser.add_option("-v", "--verbose",
                  action="store_true", dest="verbose", default=False,
                  help="Produce verbose output")
parser.add_option("-x", "--extract",
                  action="store_true", dest="extract", default=False,
                  help="Extract osc and changeset tags from from zip archive")
parser.add_option("-z", "--zipfile",
                  action="store", dest="zip_filename", default='linz_places.zip',
                  help="Name of zip file containing the OSC files to be imported")
(options, args) = parser.parse_args()

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
if (options.more != None):
   print("   more than %d addresses" % options.more)
print("")

lat_lon = re.compile('node.*lat="(.*?)".*lon="(.*?)"')
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
    to_import_places = 0
    to_import_addresses = 0

    if ((options.above != None) or 
        (options.below != None) or 
        (options.left != None)  or 
        (options.right != None)) :

      placesZip = zipfile.ZipFile(options.zip_filename)

    for row in csvreader:

        # Stop processing CSV file as soon as we get to row starting with "TOTAL"
        if row['place'] == 'TOTAL':
           break

        addresses = int(row['num_addresses'])

        row_num = row_num + 1
        total_places += 1
        total_addresses += addresses

        if (row['uploader'] == ''):
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
                      if (options.more == None) or ( addresses > options.more):
                        to_import_places += 1
                        to_import_addresses += addresses
                        print ("%s - %d addresses to be imported [%.3f,%.3f]" % (place, addresses, float(coords.group(1)), float(coords.group(2)) ) )

                        if options.extract:
                          placesZip.extract(osc_file_name)
                          placesZip.extract("linz_places/" + place + ".changeset_tags")

                        break
             except:
               print("***ERROR occured extracting %s" % osc_file_name)

           elif (options.more == None) or ( addresses > options.more):
             to_import_places += 1
             to_import_addresses += addresses
             print ("%s - %d addresses to be imported" % (place, addresses))



    print("\nTotal of %d places with %d addresses" % (total_places, total_addresses))
    print("Checked %d places still to be imported with %d addresses" % (checked_places, checked_addresses))
    print("Found %d places still to be imported with %d addresses" % (to_import_places, to_import_addresses))
