#!/usr/bin/python
import csv
import overpy
import zipfile
import re
import requests
import sys

from optparse import OptionParser

MAX_LINES_CSV = 3122
above = -34.9

#-----------------------------------------------------------------------------
# Parse command line options
#-----------------------------------------------------------------------------
if len(sys.argv) != 2:
   print("Must specify latitude above which to find places to import")
   quit()

above = float(sys.argv[1])

#-----------------------------------------------------------------------------
# Initialisation
#-----------------------------------------------------------------------------
api = overpy.Overpass()

#-----------------------------------------------------------------------------
# Read data from address import tracking spreadsheet
#-----------------------------------------------------------------------------
print("Searching for locations to be imported above %f" % above)

with open('file_list.csv', 'rb') as csvfile:
    csvreader = csv.DictReader(csvfile)
    row_num = 0
    for row in csvreader:
        row_num = row_num + 1
        if (row_num <= MAX_LINES_CSV):
           if (row['uploader'] == ''):
              place = row['place']
              #print("Checking %s" % place)

              osc_file_name = "linz_places/" + place + ".osc"
              
              lat_lon = re.compile('node.*lat="(.*?)".*lon="(.*?)"')
              with zipfile.ZipFile('linz_places.zip') as placesZip:
                with placesZip.open(osc_file_name) as osc_file:
                  for line in osc_file:
                     coords = lat_lon.search(str(line))
                     if coords and (float(coords.group(1)) > above):
                       print (place)
                       break
