#!/usr/bin/env python

#
# Copyright (C) 2010-2019 ABINIT Group (Jean-Michel Beuken)
#
# This file is part of the ABINIT software package. For license information,
# please see the COPYING file in the top-level directory of the ABINIT source
# distribution.
#

#
# 'false' errors elimination in the 'linkchecker_ext.log' generated by
# a script located on ref slave ( abiref:~buildbot/bin/LinkChecker.sh )
#

from __future__ import unicode_literals, division, print_function, absolute_import

import sys
import os
import re
from lxml import etree
import requests

# ---------------------------------------------------------------------------- #

#
# Functions
#

#all_tags = [ 'url','name','parent','realurl','extern','dlsize','checktime','level','infos','valid' ]
#printable_tags = [ 'url', 'name', 'parent', 'realurl', 'valid' ]

server="http://localhost:8000"

def rm_server(keyword):
  if keyword.startswith(server):
     return keyword[len(server):]

def Checking_on_url_to_skip(e, u, v):
  global url_to_skip
  for ui in url_to_skip :
     #print(e,u,v)
     #print(ui)
     if e == "1" and ui == u and  ( v == "syntax OK" or v == "filtered" ) :
         #print("url_to_skip")
         return True
  return False

    #  for s in url_string_to_skip :
    #     if extern.text == "1" and URL.find( s ) >= 0 :
    #        continue

def Checking_on_url_string_to_skip(e, u):
  global url_string_to_skip
  for s in url_string_to_skip :
     if e == "1" and u.find( s ) >= 0 :
         #print(s,"url_string_to_skip")
         return True
  return False

def Checking_on_no_error_list(url, info, valid):
  global no_error_list
  #print("Enter no_error_list... %s,%s,%s" % (url.text,info,valid))
  for no_error in no_error_list:

    norc = True  # True : we consider that this is not an error

    url_rc = None
    try:
       url_rc = no_error['url'].search(url.text)
    except:
       print("-- no URL NAME --")
    norc = norc and ( url_rc != None )

    info_rc = None
    if info is not None:
      try:
       info_rc = no_error['info'].search(info.text)
       norc = norc and ( info_rc != None )
      except:
       pass
    else:
       info_rc = True

    valid_rc = None
    valid_rc = no_error['valid'].search(valid)
    norc = norc and ( valid_rc != None )

    #print(" url_rc : ",url_rc," info_rc : ",info_rc,"valid_rc : ",valid_rc)
    #print("exit with : ",url_rc != None and info_rc != None and valid_rc != None)
    if url_rc != None and info_rc != None and valid_rc != None:
        return True # in the exception list -> next xml entry
  return False # may be a error

# ---------------------------------------------------------------------------- #

# Types of error :
#    Error: 403 Forbidden'
#    Error: 404 Not Found'
#    Error: 504 Gateway Time-out'
#    Error: 502 Bad Gateway'
#    Error: ReadTimeout:'
#    ConnectionError: ('Connection aborted.'

no_error_list = [
    { 'url'  : re.compile('(doi|aps).org'),
      'info' : re.compile('^Redirected'),
      'valid': re.compile('^403 Forbidden')
    },
    { 'url'  : re.compile('jstor.org'),
      'valid': re.compile('^403 Unauthorized')
    },
]

url_to_skip = [
    "https://github.com/abinit/abiconfig",
    "https://github.com/abinit/abiflows",
    "https://github.com/abinit/abiconda",
    "https://github.com/abinit/abiconfig",
    "https://github.com/abinit/abitutorials",
    "https://github.com/abinit/abipy",
    "https://github.com/abinit/abiout",
    "https://github.com/abinit/abinit/",
    "https://github.com/abinit/abinit",
    "https://github.com/abinit/",
    "https://github.com/abinit",
    "https://www.facebook.com/abinit.org",
    "https://fonts.gstatic.com"
]

url_string_to_skip = [
    "cdn.jsdelivr.net",
    "cdn.embedly.com",
    "cdn.plot.ly",
    "maxcdn.bootstrapcdn.com",
    "facebook.com/abinit",
    "github.com/abinit/abinit/edit",
    "markdown-here/wiki/Markdown",
    "nschloe/betterbib",
    "github.com/mitya57",
    "github.com/helderco",
    "github.com/abinit/abinit/commit/",
    "github.com/abinit/abipy_assets",
    "github.com/abinit/abinit/tree",
    "github.com/abinit/abinit/blob",

]

# ---------------------------------------------------------------------------- #

#
# Main program
#
def main(filename,home_dir=""):
  from os.path import join as pj

  # Check if we are in the top of the ABINIT source tree
  my_name = os.path.basename(__file__) + ".main"
  if ( not os.path.exists(pj(home_dir,"configure.ac")) or
       not os.path.exists(pj(home_dir, "src/98_main/abinit.F90")) ):
    print("%s: You must be in the top of an ABINIT source tree." % my_name)
    print("%s: Aborting now." % my_name)
    sys.exit(1)

  #
  tree = etree.parse(filename)
  
  rc=0
  for child in tree.xpath("/linkchecker/urldata"):
  
    url    = child.find('url')
    URL    = url.text
    info   = child.find('infos/info')
    extern = child.find('extern')
    valid  = child.find('valid').get("result")

    ### precleaning ###

    v = re.compile("^200")   # status "200" or "200 OK"
    if v.search(valid):
       continue

    if url.text[0:6] == "mailto" and valid == "Valid mail address syntax" :
       continue

    if Checking_on_url_to_skip( extern.text, url.text, valid ):
       continue

    if Checking_on_url_string_to_skip( extern.text, url.text ):
       continue

    ### fine cleaning ###

    if Checking_on_no_error_list(url, info, valid) :
       continue

    ### last chance to know if it's not a error ###
    ### access denied  then checks with 'curl'  ###

    Check_connection = False
    if valid == "syntax OK" :
        Check_connection = True
        request = requests.get(url.text, headers={"content-type":"text"}, timeout=(2,2) )
        #print(r.request.headers)
        if request.status_code == 200 :
            continue

    # found a true error... : reporting on bb
    rc += 1
    name=child.find('name')
    parent=child.find('parent')
    realurl=child.find('realurl')
    try:
       print("{0:12} {1}".format('URL',url.text))
    except:
       print("{0:12} {1}".format('URL',' ** NO URL **'))
    try:
       print("{0:12} {1}".format('Name',name.text))
    except:
       print("{0:12} {1}".format('Name','** NO NAME **'))
    print("{0:12} {1}, line {2}".format('Parent URL',rm_server(parent.text),parent.get('line')))
    try:
       print("{0:12} {1}".format('Infos',info.text))
    except:
       pass 
    print("{0:12} {1}".format('Real URL',realurl.text))
    print("{0:12} {1}".format('Result',valid))
    if Check_connection : 
          print("{0:12} {1}".format('Status CNX',request.status_code))
    print('---------------------------')

  return rc

# ---------------------------------------------------------------------------- #

if __name__ == "__main__":
  
  try:
    filename = sys.argv[1]
  except:
    print("filename missing...")
    sys.exit(1)

  if len(sys.argv) == 2:
    home_dir = "."
  else:
    home_dir = sys.argv[2]

  exit_status = main(filename,home_dir)
  sys.exit(exit_status)
