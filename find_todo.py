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
parser.add_option("-r", "--right", dest="right", type="float", 
                  help="Specify longitude right of which to find places to import")
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
print("Searching for locations still to to be imported")
if (options.above != None):
   print("   above (north of) %f" % options.above)
if (options.below != None):
   print("   below (south of) %f" % options.below)
if (options.left != None):
   print("   left (west) of %f" % options.left)
if (options.right != None):
   print("   right (east) of %f" % options.right)

lat_lon = re.compile('node.*lat="(.*?)".*lon="(.*?)"')
#-----------------------------------------------------------------------------
# Read data from address import tracking spreadsheet
#-----------------------------------------------------------------------------
with open(options.list_filename, 'rt') as csvfile:
    csvreader = csv.DictReader(csvfile)
    row_num = 0
    places=0
    checked = 0
    found = 0
    total_num = 0
    for row in csvreader:
        row_num = row_num + 1
        places += 1

        # Stop processing CSV file as soon as we get to row starting with "TOTAL"
        if row['place'] == 'TOTAL':
           break

        if (row['uploader'] == ''):
           checked += 1
           place = row['place']
           num = int(row['num_addresses'])
           if options.verbose:
              print("Checking %s" % place)

           osc_file_name = "linz_places/" + place + ".osc"
           
           with zipfile.ZipFile(options.zip_filename) as placesZip:
             try:
                with placesZip.open(osc_file_name) as osc_file:
                  for line in osc_file:
                     coords = lat_lon.search(str(line))
                     if coords and \
                        (((options.above == None) or (float(coords.group(1)) > options.above)) and
                         ((options.below == None) or (float(coords.group(1)) < options.below)) and
                         ((options.left == None)  or (float(coords.group(2)) < options.left)) and
                         ((options.right == None) or (float(coords.group(2)) > options.right))):
                       found += 1
                       total_num += num
                       print ("%s - to be imported, Lat %.3f Long %.3f %d addresses" % (place, float(coords.group(1)), float(coords.group(2)), num))
                       break
             except:
                print("***ERROR occured extracting %s" % osc_file_name)

    print("Total of %d places with %d addresses" % (places, total_num))
    print("Checked %d places still to be imported" % checked)
    print("Found %d places still to be imported" % found)
