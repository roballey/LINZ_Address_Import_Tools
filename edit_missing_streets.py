#!/usr/bin/python
import requests
from optparse import OptionParser
import sys
import re

def edit(objects):
   #proxies = {
   #   "http" : "http://127.0.0.1:3128",
   #   "https" : "https://127.0.0.1:3128"
   #   }
   print("   JOSM: http://127.0.0.1:8111/load_object?new_layer=true&objects=%s" % objects)
   #requests.get("http://127.0.0.1:8111/load_object?new_layer=true&objects=%s" % objects, proxies=proxies)
   requests.get("http://127.0.0.1:8111/load_object?new_layer=true&objects=%s" % objects)
   raw_input("Press enter to continue...")
   return

place_regex=re.compile("^(.\+)")
street_regex=re.compile("^   (.*?),(.*?)$")

#-----------------------------------------------------------------------------
# Parse command line options
#-----------------------------------------------------------------------------
parser = OptionParser()
parser.add_option("-v", "--verbose",
                  action="store_true", dest="verbose", default=False,
                  help="Produce verbose output")
(options, args) = parser.parse_args()

if (len(args) != 1):
   print("Must specify input file on the command line")
   quit()

infile = open(args[0], "rt")

objects = ''
for line in infile:
   place = place_regex.search(line)
   if place:
      if options.verbose:
         print("Place '%s'" % place.group(1))
      if objects != '':
         edit(objects)
         objects = ''
      
   else:
      street = street_regex.search(line)
      if street:
         if options.verbose:
            print("   Street '%s', Id: %s" % (street.group(1), street.group(2)))
         objects = objects + 'n' + str(street.group(2)) + ','

if objects != '':
   edit(objects)
   objects = ''

infile.close()
