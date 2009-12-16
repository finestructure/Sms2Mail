# -*- coding: utf-8 -*-
# Author: Sven A. Schmidt
# Email: sas@abstracture.de
# Revision: $Id$

import sys
import os
from Foundation import *
import sqlite3
import datetime
import hashlib
import tempfile
import ConfigParser
import imaplib
import time
import pickle
import AddressBook
import email
import glob
from email.message import Message

config_filename = os.path.expanduser('~/.sms2mail.conf')
cache_filename = os.path.expanduser('~/.sms2mail.cache')

# could be a config option but it's probably not necessary
BACKUPDIR = os.path.expanduser('~/Library/Application Support/'
                               'MobileSync/Backup')


def listDevices(toplevelDir=None):
  res = []
  if toplevelDir is None:
    pattern = BACKUPDIR + '/*/Info.plist'
  else:
    pattern = toplevelDir + '/Info.plist'
  for f in glob.glob(pattern):
    plist = NSDictionary.dictionaryWithContentsOfFile_(f)
    dev = {'Backup Directory' : f[:-len('/Info.plist')]}
    for key in ('Device Name', 'Product Version', 'Product Type', 
              'Last Backup Date', 'Serial Number', 'Phone Number'):
      dev[key] = plist.objectForKey_(key)
    res.append(dev)
  # sort the result from latest to earliest backup
  return sorted(res, 
                lambda x,y: -cmp(x['Last Backup Date'], y['Last Backup Date']))


def findLatestBackupDir():
  dirs = {}
  for p in os.listdir(BACKUPDIR):
    path = os.path.join(BACKUPDIR, p)
    if os.path.isdir(path):
      dirs[os.path.getmtime(path)] = path
  keys = sorted(dirs.keys())
  return dirs[keys[-1]]


def findSqliteFile(backupSubdir):
  for root, dirs, files in os.walk(backupSubdir):
    for f in files:
      if f.endswith('mdinfo'):
        try:
          path = os.path.join(root, f)
          plist = NSDictionary.dictionaryWithContentsOfFile_(path)
          data = plist.objectForKey_('Metadata')
          plist, _, _ = NSPropertyListSerialization.\
              propertyListFromData_mutabilityOption_format_errorDescription_\
              (data, 0, None, None)
          if plist.objectForKey_('Path') == 'Library/SMS/sms.db':
            return os.path.join(root, f.replace('mdinfo', 'mddata'))
        except:
          pass
  return None


def getSqliteFile():
  """
  Save the sms sqlite database from the backup in a temp file.
  Returns the temp file object.
  """
  sqlitefilename = findSqliteFile(findLatestBackupDir())
  temp = tempfile.NamedTemporaryFile()
  temp.write(open(sqlitefilename).read())
  temp.flush()
  return temp, sqlitefilename


def getGroups(sqlitedb):
  """
  Get the groups from the sqlite database.
  """
  cursor = sqlitedb.cursor()

  groups = {}
  cursor.execute('select group_id, address '
                 'from group_member order by address')
  for g, a in cursor.fetchall():
    a = lookupName(a)
    if g not in groups.keys():
        groups[g] = [a]
    else:
        groups[g].append(a)
  return groups


def createMessage(sender, receiver, subject, timestamp, sms_id, body):
  try:
    msg = Message()
    msg.add_header('From', sender.encode('utf-8'))
    msg.add_header('Subject', subject.encode('utf-8'))
    msg.add_header('Date', str(datetime.datetime.fromtimestamp(timestamp)))
    msg.add_header('To', receiver.encode('utf-8'))
    msg.add_header('Sms-Id', sms_id)
    msg.set_payload(body.encode('utf-8'))
    msg.timestamp = time.localtime(timestamp)
    msg.sms_id = sms_id
    email.encoders.encode_quopri(msg)
    msg.set_charset('utf-8')
    return msg
  except:
    print sender, type(sender)
    print receiver
    print subject
    print timestamp
    print sms_id
    print body
    raise


def getMessages(sqlitedb, mynumber):
  """
  Create a message dictionary for each sms text message in the sqlite
  database.
  Returns a list of message dictionaries with keys: id, time, message
  id: A unique hash generated from the address, the date, the flags,
      and the group. This hash is used to make sure a message is uploaded
      only once.
  time: Timestamp of the sms message in seconds since the epoch.
  message: The sms text message body.
  """
  groups = getGroups(sqlitedb)
  me = lookupName(mynumber)
  cursor = sqlitedb.cursor()
  messages = []
  
  cursor.execute('select address, date, text, flags, group_id '
                 'from message order by date')
  for phone_number, timestamp, body, flags, group_id in cursor.fetchall():
    if phone_number is None or body is None:
      continue
    
    other = lookupName(phone_number)        
    subject = ('Conversation with %s (Group %d)') % (
                          ', '.join(groups[group_id]), group_id)
    if flags == 2: # to me
      sender = other
      receiver = me
    elif flags == 3: # from me
      sender = me
      receiver = other
    else: # default (seen flags 2050 from voice box)
      sender = other
      receiver = me
    sms_id = hashlib.sha1('%s%d%d%d' % (
                          phone_number, timestamp, flags, group_id)).hexdigest()    
    
    msg = createMessage(sender, receiver, subject, timestamp, sms_id, body)

    messages.append(msg)
  
  return messages            


def readExistingIdsCache():
  if not os.path.exists(cache_filename):
    return set()
  else:
    cache = open(cache_filename)
    res = pickle.load(cache)
    cache.close()
    return res


def getSmsId(header):
  """
  Parse the SmsId fields from a header block.
  """
  for line in header.split('\r\n'):
    if line.startswith('Sms-Id:'):
      line = line[len('Sms-Id:'):].strip()
      return line
  return None


def fetchExistingIds(imap_connection):
  """
  Fetch the list of sms ids already on the IMAP server. Every message
  has a header 'Sms-Id' with the unique text message hash.
  """
  existing_ids = set()
  
  t, data = imap_connection.fetch('1:*', '(BODY.PEEK[HEADER])')
  for response_part in data:
    if isinstance(response_part, tuple):
      header = response_part[1]
      existing_ids.add(getSmsId(header))
  
  return existing_ids


def uploadMessages(messages):
  """
  Uploads new messages to the IMAP server. New messages are identified by
  their sms_id. Only messages with ids not already present on the server
  are uploaded.
  """
  print 'Reading id cache from disk'
  cached_ids = readExistingIdsCache()
  print 'Found %d entries' % len(cached_ids)
  
  # check if there are any new messags at all against the cache
  # before hitting the IMAP server
  new_messages = []
  for msg in messages:
    if msg.sms_id not in cached_ids:
      new_messages.append(msg)

  print 'New message count:', len(new_messages)

  if len(new_messages) == 0:
    return
  
  # there are messages left which are not in our cache, refresh it now
  print 'Connecting to IMAP server %s:%s...' % (host, str(port))
  M = imaplib.IMAP4_SSL(host=host, port=port)
  M.login(user, password)    
  M.select(sms_mailbox)

  # unite both sets (cache and refreshed ones) and save them in the cache
  # the reason we don't simply overwrite the cache is that this way if a
  # user has deleted sms mails they won't be resynched -- this will only
  # happen when the cache is manually reset or the script is run from 
  # another machine
  print 'Fetching existing ids from the server...'
  server_ids = fetchExistingIds(M)
  print 'Found %d ids on the server.' % len(server_ids)
  existing_ids = cached_ids.union(server_ids)
  print 'Total existing ids: %d' % len(existing_ids)
  cache = open(cache_filename, 'w')
  pickle.dump(existing_ids, cache)
  cache.close()
  
  print 'Uploading new messages...'
  new_count = 0
  skipped_count = 0
  for index, msg in enumerate(new_messages):
    if msg.sms_id not in existing_ids:
      print 'Saving %d %s' % (index, msg.sms_id)
      flags = None
      date = time.localtime(msg['time'])
      res, _ = M.append(sms_mailbox, flags, msg.timestamp, msg.as_string())
      print '  ', res
      if res == 'OK':
        new_count += 1
    else:
      #print 'Skipping %d %s' % (index, msg['id'])
      skipped_count += 1
  print 'New messages uploaded:', new_count
  print 'Skipped (previously uploaded):', skipped_count

  M.close()
  M.logout()


def filterDigits(string):
  digits = '0123456789'
  return ''.join([c for c in string if c in digits])


# shamelessly stolen from the PyObjC example shipping w/ Xcode and adapted


def encodeField(value):
  """
  Encode a value into an UTF-8 string
  """
  if value is None:
    return ''

  if isinstance(value, AddressBook.ABMultiValue):
    # A multi-valued property, merge them into a single string
    result = []
    for i in range(len(value)):
      result.append(value.valueAtIndex_(i))
    return result

  return value


def getPhonebook():
  """
  Creat a 'phonebook', i.e. a dictionary {'123456':'John Doe'}.
  The reason we're doing this instead of using the AB search API is that
  the API has no way to suppress spaces and extra characters like dashes,
  slashes etc. If an entry has a phone number '49 171 123456' it will not
  show up when searching for '49171123456'. (Quite strange that, the
  AddressBook application ignores whitespace, it must use another mechanism.)
  """
  phonebook = {}
  book = AddressBook.ABGetSharedAddressBook()
  fields = ( AddressBook.kABPhoneProperty,
             AddressBook.kABFirstNameProperty,
             AddressBook.kABLastNameProperty)

  for person in book.people():
    record = [ encodeField(person.valueForProperty_(i)) for i in fields ]
    for phonenumber in [filterDigits(i) for i in record[0]]:
      phonebook[phonenumber] = ' '.join([record[1], record[2]])
  return phonebook


phonebook = getPhonebook()

def lookupName(number):
  digitsonly = filterDigits(number)
  try:
    return phonebook[digitsonly]
  except KeyError:
    # try a little harder to match numbers like 0171 with 49171
    if digitsonly.startswith('0') or digitsonly.startswith('00'):
      digitsonly = digitsonly.lstrip('0')
      for n in phonebook.keys():
        if n.endswith(digitsonly):
          return phonebook[n]
    return number


if __name__ == '__main__':

  # get options
  print 'Reading config' 
  config = ConfigParser.ConfigParser()
  config.read(config_filename)
  
  user = config.get('IMAP', 'user')
  password = config.get('IMAP', 'password')
  sms_mailbox = config.get('IMAP', 'sms_mailbox')
  host = config.get('IMAP', 'host')
  try:
    port = config.get('IMAP', 'port')
  except ConfigParser.NoOptionError:
    port = 993 # IMAP SSL
  mynumber = config.get('Phone', 'mynumber')

  print 'Looking for sms sqlite file ...'
  sqlitefile, fname = getSqliteFile()
  print '... found:', fname
  print 'Connecting with sqlite3 ...'
  sqlitedb = sqlite3.connect(sqlitefile.name)
  print '... successful.'
  
  print 'Getting messages from sqlite db ...'
  messages = getMessages(sqlitedb, mynumber)
  print '... found %d messages' % len(messages)
  
  print 'Uploading messages to IMAP account %s@%s' % (user, host)
  uploadMessages(messages)
    
      
