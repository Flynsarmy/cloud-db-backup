#!/usr/bin/python
#
# Copyright 2009 Google Inc. All Rights Reserved.
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
__credits__ = "e.bidelman@google.com (Eric Bidelman)"

import getopt
import mimetypes
import os.path
import inspect
import sys
import atom.data
import gdata.client
import gdata.data
import gdata.docs.client
import gdata.docs.data


APP_NAME = 'flynsarmy-gdocs-backup-v1'


def get_mimetype(filename):
  file_ext = filename[filename.rfind('.'):]
  if file_ext in mimetypes.types_map:
    content_type = mimetypes.types_map[file_ext]
  else:
    content_type = 'application/x-'+file_ext

  return content_type


class ResumableUploadDemo(object):
  """Helper class to setup a resumable upload, and upload a file."""

  CREATE_SESSION_URI = '/feeds/upload/create-session/default/private/full'

  client = None  # A gdata.client.GDClient object.
  prefs = []
  uploader = None  # A gdata.client.ResumableUploader object.

  def __init__(self, email, password, filepath, chunk_size=None,
               convert=None, host=None, ssl=True, debug=False):

    self.convert = convert
    self.debug = debug

    if chunk_size:
      self.chunk_size = chunk_size

    # Authenticate the user with CLientLogin
    try:
      self.client = gdata.docs.client.DocsClient(source=APP_NAME)
      self.client.ssl = ssl  # Force all API requests through HTTPS
      self.client.http_client.debug = self.debug  # Set to True for debugging HTTP requests
      self.client.ClientLogin(email, password, self.client.source);

    except gdata.client.BadAuthentication:
      exit('Invalid user credentials given.')
    except gdata.client.Error:
      exit('Login Error')

    mimetypes.init()  # Register common mimetypes on system.

    self.f = open(filepath)
    content_type = get_mimetype(self.f.name)
    file_size = os.path.getsize(self.f.name)

    self.uploader = gdata.client.ResumableUploader(
        self.client, self.f, content_type, file_size,
        chunk_size=self.chunk_size, desired_class=gdata.docs.data.DocsEntry)

  def __del__(self):
    if self.uploader is not None:
      self.uploader.file_handle.close()

  def UploadAutomaticChunks(self, new_entry):
    """Uploads an entire file, handing the chunking for you.

    Args:
      new_entry: gdata.data.docs.DocsEntry An object holding metadata to create
          the document with.

    Returns:
      A gdata.docs.data.DocsEntry of the created document on the server.
    """
    uri = self.CREATE_SESSION_URI

    # If convert=false is used on the initial request to start a resumable
    # upload, the document will be treated as arbitrary file upload.
    if self.convert is not None:
      uri += '?convert=' + self.convert

    return self.uploader.UploadFile(uri, entry=new_entry)

  def UploadInManualChunks(self, new_entry):
    """Uploads a file, demonstrating manually chunking the file.

    Args:
      new_entry: gdata.data.docs.DocsEntry An object holding metadata to create
          the document with.

    Returns:
      A gdata.docs.data.DocsEntry of the created document on the server.
    """
    uri = self.CREATE_SESSION_URI

    # If convert=false is used on the initial request to start a resumable
    # upload, the document will be treated as arbitrary file upload.
    if self.convert is not None:
      uri += '?convert=' + self.convert

    # Need to create the initial session manually.
    self.uploader._InitSession(uri, entry=new_entry)

    start_byte = 0
    entry = None

    while not entry:
      if self.debug:
        print 'Uploading bytes: %s-%s/%s' % (start_byte,
                                             self.uploader.chunk_size - 1,
                                             self.uploader.total_file_size)
      entry = self.uploader.UploadChunk(
          start_byte, self.uploader.file_handle.read(self.uploader.chunk_size))
      start_byte += self.uploader.chunk_size

    return entry

def main():
  email = None
  password = None
  filepath = None
  convert = 'false'  # Convert to Google Docs format by default
  default_chunk_size = gdata.client.ResumableUploader.DEFAULT_CHUNK_SIZE;
  chunk_size = default_chunk_size
  debug = False
  ssl = True

  try:
    opts, args = getopt.getopt(
        sys.argv[1:], '', ['email=', 'password=', 'filepath=',
                           'convert', 'chunk_size=', 'ssl',
                           'debug'])

  except getopt.error, msg:
    print 'python '+inspect.getfile( inspect.currentframe() )+'''
        --email= [your Google Docs email]
        --password= [your Google Docs password]
        --filepath= [file to upload]
        --convert [converts uploaded file]
        --chunk_size= [size of upload chunks. default is '''+str(default_chunk_size)+''']
        --nossl [disables HTTPS if set]
        --debug [prints debug info if set]'''
    print ('Example usage: '+inspect.getfile( inspect.currentframe() )+' '
           '--filepath=/path/to/test.doc --convert --nossl')
    sys.exit(2)

  for option, arg in opts:
    if option == '--email':
      email = arg
    elif option == '--password':
      password = arg
    elif option == '--filepath':
      filepath = arg
    elif option == '--convert':
      convert = 'true'
    elif option == '--chunk_size':
      chunk_size = int(arg)
    elif option == '--nossl':
      ssl = False
    elif option == '--debug':
      debug = True

  if email is None:
    exit('Google Docs email address required but not given. Use --email=<your email>')
  elif password is None:
    exit('Google Docs password required but not given. Use --password=<your password>');
  elif filepath is None:
    exit('Filepath required but not given. Use --filepath=<path/to/file>')

  demo = ResumableUploadDemo(email, password, filepath,
                             chunk_size=chunk_size, convert=convert,
                             ssl=ssl, debug=debug)

  title = os.path.basename( filepath )

  if debug:
    print 'Uploading %s ( %s ) @ %s bytes...' % (demo.uploader.file_handle.name,
                                                 demo.uploader.content_type,
                                                 demo.uploader.total_file_size)

  if chunk_size != gdata.client.ResumableUploader.DEFAULT_CHUNK_SIZE:
    entry = demo.UploadAutomaticChunks(
        gdata.docs.data.DocsEntry(title=atom.data.Title(text=title)))
  else:
    entry = demo.UploadInManualChunks(
        gdata.docs.data.DocsEntry(title=atom.data.Title(text=title)))

  if debug:
    print 'Done: %s' % demo.uploader.QueryUploadStatus()
    print 'Document uploaded: ' + entry.title.text
    print 'Quota used: %s' % entry.quota_bytes_used.text

    print 'file closed: %s' % demo.uploader.file_handle.closed

if __name__ == '__main__':
  main()