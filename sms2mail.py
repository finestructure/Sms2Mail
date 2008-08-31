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

config_filename = '~/.sms2mail.conf'


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


def getGroups(connection):
    """
    Get the groups from the sqlite database.
    """
    cursor = connection.cursor()

    groups = {}
    cursor.execute('select group_id, address '
                   'from group_member order by address')
    for g, a in cursor.fetchall():
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
    groups = getGroups(conn)

    cursor = connection.cursor()

    messages = []
    cursor.execute('select address, date, text, flags, group_id '
                'from message order by date')
    for a, d, t, f, g in cursor.fetchall():
        if a is None or t is None:
            continue
        if filter is not None and filter not in a:
            continue
        subject = ('Subject: Conversation with '
                   '%s (Group %d)') % (', '.join(groups[g]), g)
        if f == 2: # to me
            sender = 'From: ' + a
            recipient = 'To: ' + mynumber
        elif f == 3: # from me
            sender = 'From: ' + mynumber
            recipient = 'To: ' + a
        else: # default (seen flags 2050 from voice box)
            sender = 'From: ' + a
            recipient = 'To: ' + mynumber
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


def getExistingIds(imap_connection):
    """
    Gets the lists of sms ids already on the IMAP server. Every message
    has a header 'Sms-Id' with the unique text message hash.
    """
    existing_ids = []
    
    t, data = imap_connection.search(None, 'ALL')
    for num in data[0].split():
        t, data = imap_connection.fetch(num, '(RFC822)')
        msgtext = data[0][1]
        for line in msgtext.split('\r\n'):
            if line.startswith('Sms-Id:'):
                existing_ids.append(line.split()[1])
    
    return existing_ids


def uploadMessages(messages):
    """
    Uploads new messages to the IMAP server. New messages are identified by
    their sms_id. Only messages with ids not already present on the server
    are uploaded.
    """
    M = imaplib.IMAP4_SSL(host=host, port=port)
    M.login(user, password)    
    M.select(sms_mailbox)

    existing_ids = getExistingIds(M)
    
    for msg in messages:
        if msg['id'] not in existing_ids:
            flags = ''
            date = time.localtime(msg['time'])
            print M.append(sms_mailbox, flags, date, msg['message'])

    M.close()
    M.logout()


if __name__ == '__main__':

    # could be a config option but it's probably not necessary
    backupdir = os.path.expanduser('~/Library/Application Support/'
                                   'MobileSync/Backup')

    # get options    
    config = ConfigParser.ConfigParser()
    config.read(os.path.expanduser(config_filename))
    
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
    
      
