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

config_filename = os.path.expanduser('~/.sms2mail.conf')
cache_filename = os.path.expanduser('~/.sms2mail.cache')


def getSmsPlist(backupdir):
    """
    Find the plist file containing the sms sqlite database.
    Returns the plist file.
    """
    for root, dirs, files in os.walk(backupdir):
        for f in files:
            if f.endswith('mdbackup'):
                path = os.path.join(root, f)
                plist = NSDictionary.dictionaryWithContentsOfFile_(path)
                if plist != None:
                    if plist.objectForKey_('Path') == 'Library/SMS/sms.db':
                        return plist


def getSqliteFile(backupdir):
    """
    Save the sqlite database from the backup in a temp file.
    Returns the temp file object.
    """
    temp = tempfile.NamedTemporaryFile()
    plist = getSmsPlist(backupdir)
    data = plist.objectForKey_('Data')
    data.writeToFile_atomically_(temp.name, True)
    return temp


def getGroups(connection, phonebook):
    """
    Get the groups from the sqlite database.
    """
    cursor = connection.cursor()

    groups = {}
    cursor.execute('select group_id, address '
                   'from group_member order by address')
    for g, a in cursor.fetchall():
        a = filter_digits(a)
        try:
            a = phonebook[a]
        except KeyError:
            pass
        if g not in groups.keys():
            groups[g] = [a]
        else:
            groups[g].append(a)
    return groups


def createMessages(connection, mynumber, filter=None):
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
    phonebook = getPhonebook()
    groups = getGroups(conn, phonebook)
    
    mynumber = filter_digits(mynumber)
    try:
        me = phonebook[mynumber]
    except KeyError:
        me = mynumber

    cursor = connection.cursor()

    messages = []
    cursor.execute('select address, date, text, flags, group_id '
                'from message order by date')
    for a, d, t, f, g in cursor.fetchall():
        if a is None or t is None:
            continue
        if filter is not None and filter not in a:
            continue
        
        a = filter_digits(a)
        try:
            other = phonebook[a]
        except KeyError:
            other = a
        
        subject = ('Subject: Conversation with '
                   '%s (Group %d)') % (', '.join(groups[g]), g)
        if f == 2: # to me
            sender = 'From: %s' % other
            recipient = 'To: %s' % me
        elif f == 3: # from me
            sender = 'From: %s' % me
            recipient = 'To: %s' % other
        else: # default (seen flags 2050 from voice box)
            sender = 'From: %s' % other
            recipient = 'To: %s' % me
        date = 'Date: %s' % datetime.datetime.fromtimestamp(d)
        sms_id = hashlib.sha1('%s%d%d%d' % (a,d,f,g)).hexdigest()
        sms_id_header = 'Sms-Id: ' + sms_id
        
        # FIXME: find a unicode preserving encoding method
        # base64?
        body = ('\r\n%s' % t).encode('ascii', 'replace')
        
        msg = '\r\n'.join([sender, subject, date, recipient, 
                           sms_id_header, body])

        messages.append({'id':sms_id, 'time':d, 'message' : msg})
    
    return messages            


def readExistingIdsCache():
    if not os.path.exists(cache_filename):
        return set()
    else:
        cache = open(cache_filename)
        res = pickle.load(cache)
        cache.close()
        return res


def getExistingIds(imap_connection):
    """
    Gets the lists of sms ids already on the IMAP server. Every message
    has a header 'Sms-Id' with the unique text message hash.
    """
    existing_ids = set()
    
    t, data = imap_connection.search(None, 'ALL')
    for num in data[0].split():
        t, data = imap_connection.fetch(num, '(RFC822)')
        msgtext = data[0][1]
        for line in msgtext.split('\r\n'):
            if line.startswith('Sms-Id:'):
                existing_ids.add(line.split()[1])
    
    return existing_ids


def uploadMessages(messages):
    """
    Uploads new messages to the IMAP server. New messages are identified by
    their sms_id. Only messages with ids not already present on the server
    are uploaded.
    """
    cached_ids = readExistingIdsCache()
    # check if there are any new messags at all against the cache
    # before hitting the IMAP server
    for msg in messages:
        if msg['id'] in cached_ids:
            messages.remove(msg)
    if messages == []:
        return
    
    # there are messages left which are not in our cache, refresh it now
    M = imaplib.IMAP4_SSL(host=host, port=port)
    M.login(user, password)    
    M.select(sms_mailbox)

    # unite both sets (cache and refreshed ones) and save them in the cache
    # the reason we don't simply overwrite the cache is that this way if a
    # user has deleted sms mails they won't be resynched -- this will only
    # happen when the cache is manually reset or the script is run from 
    # another machine
    server_ids = getExistingIds(M)
    existing_ids = cached_ids.union(server_ids)
    cache = open(cache_filename, 'w')
    pickle.dump(existing_ids, cache)
    cache.close()
        
    for msg in messages:
        if msg['id'] not in existing_ids:
            flags = ''
            date = time.localtime(msg['time'])
            M.append(sms_mailbox, flags, date, msg['message'])

    M.close()
    M.logout()


def filter_digits(string):
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
            result.append(value.valueAtIndex_(i).encode('utf-8'))
        return result

    return value.encode('utf-8')


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
        for phonenumber in [filter_digits(i) for i in record[0]]:
            phonebook[phonenumber] = ' '.join([record[1], record[2]])
    return phonebook



if __name__ == '__main__':

    # could be a config option but it's probably not necessary
    backupdir = os.path.expanduser('~/Library/Application Support/'
                                   'MobileSync/Backup')

    # get options    
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

    sqlitefile = getSqliteFile(backupdir)
    conn = sqlite3.connect(sqlitefile.name)
    
    messages = createMessages(conn, mynumber)
    
    uploadMessages(messages)
    
      
