#!/usr/bin/env python
#
# Copyright 2011 Flynsarmy. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

__author__ = 'flynsarmy@gmail.com (Flynsarmy)'
__version__ = "1.0"
__licence__ = "Apache 2.0"

#mysqldump -umanaccom --databases dbname --extended-insert > dumpname.sql
import sys
import getopt
import inspect

#Vars that can be overridden
filepath = None
output_filepath = None
max_chunk_size = 1024000 #Google docs document limit
#Vars we'll need
debug = False
buffer_size = 0
file_count = 0
buffer = buffer_over = []

#Allow option overrides
try:
    opts, args = getopt.getopt(
        sys.argv[1:], '', ['filepath=', 'max_chunk_size=', 'debug']
    )
except getopt.error, msg:
    print 'python '+inspect.getfile( inspect.currentframe() )+'''
            --filepath= [file to upload]
            --max_chunk_size= [Maximum character count per file. Default is '''+str(max_chunk_size)+''']
            --debug [prints debug info if set]'''
    print ('Example usage: '+inspect.getfile( inspect.currentframe() )+' '
            '--filepath=/path/to/test.doc --convert --nossl')
    sys.exit(2)

for option, arg in opts:
    if option == '--filepath':
        filepath = output_filepath = arg
    elif option == '--max_chunk_size':
        max_chunk_size = int(arg)
    elif option == '--debug':
        print "INFO: Debug mode enabled"
        debug = True

#Override Sanitization
if filepath is None:
    if debug: print "ERROR: No input filepath specified"
    sys.exit(1)
if max_chunk_size <= 1:
    if debug: print "ERROR: Chunk size must be at least 2"
    sys.exit(1)

if debug:
    print "INFO: filepath set to "+filepath
    print "INFO: max_chunk_size set to "+str(max_chunk_size)

#If the input file doesn't exist, exit
try:
    File = open(filepath, "r")
except IOError as e:
    if debug: print "ERROR: Input file doesn't exist"
    sys.exit(1)

#Flush the buffer to the output file
def flush_buffer( buffer ):
    global file_count
    path = filepath+'.'+str(file_count)+'.txt'
    print path
    try:
        File_out = open(filepath+'.'+str(file_count)+'.txt', 'w')
    except IOError as e:
        if debug: print "ERROR: Cannot open output file for writing: " + path
        sys.exit(1)
    File_out.write("".join(buffer))
    File_out.close()
    file_count += 1

#Continue reading until we've got the whole file
line = File.readline()
while line:
    buffer.append( line )
    buffer_size += len(line)

    #We're over the gdocs limit. Reduce the buffer to an acceptable size and flush
    if buffer_size > max_chunk_size:
        #Find the nearest blank line. That's where we'll do the split
        overline = ''
        buffer_over_size = 0
        buffer_over = []
        while overline[0:6] != 'INSERT' and len(overline) > 1:
            overline = buffer.pop()
            buffer_over_size += len(overline)
            buffer_over.insert(0, overline )

        #Flush the buffer to the output file
        flush_buffer( buffer )


        #Re-initialize the buffer with the extra data we weren't able to write earlier
        buffer = buffer_over
        buffer_size = buffer_over_size


    line = File.readline()

#Input file has been completely read. Clear the buffer into another chunk file
if buffer_size:
    flush_buffer( buffer )