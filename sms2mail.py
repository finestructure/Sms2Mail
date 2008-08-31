# -*- coding: utf-8 -*-
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

mynumber = '+491712169993'

def getSmsPlist(backupdir):
    for root, dirs, files in os.walk(backupdir):
        for f in files:
            if f.endswith('mdbackup'):
                #print 'reading:', f
                path = os.path.join(root, f)
                plist = NSDictionary.dictionaryWithContentsOfFile_(path)
                if plist != None:
                    if plist.objectForKey_('Path') == 'Library/SMS/sms.db':
                        return plist

def getSqliteFile(backupdir):
    temp = tempfile.NamedTemporaryFile()
    plist = getSmsPlist(backupdir)
    data = plist.objectForKey_('Data')
    data.writeToFile_atomically_(temp.name, True)
    return temp


def createMessage(sender, recipient):
    subject = 'Conversation with 01736119016 (id 57)'
    sender = '+491736119016'
    recipient = '+491712169993'
    sms_id = '2f6480926b0d1e004fdd3dd9ef8eb9c09c564c58'
    
    message = ''
    message += 'Sms-Id: %s\r\n' % sms_id
    message += 'Date: %s\r\n' % time.ctime(1218643812)
    message += 'Subject: New Test\r\n'
    message += 'From: %s\r\n' % sender
    message += 'To: %s\r\n' % recipient
    message += '\r\n'
    message += 'blah text here'


def getGroups(connection):
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


def createMessages(connection, filter=None):
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

    if len(sys.argv) < 2:
        backupdir = os.environ['HOME'] + '/Library/Application Support/MobileSync/Backup'
        #backupdir = os.environ['HOME'] + '/Downloads/Backup'
    else:
        backupdir = sys.argv[1]

    # get options    
    config = ConfigParser.ConfigParser()
    config.read(os.path.expanduser('~/.sms2mail.conf'))
    
    user = config.get('IMAP', 'user')
    password = config.get('IMAP', 'password')
    sms_mailbox = config.get('IMAP', 'sms_mailbox')
    host = config.get('IMAP', 'host')
    try:
        port = config.get('IMAP', 'port')
    except ConfigParser.NoOptionError:
        port = 993 # IMAP SSL


    sqlitefile = getSqliteFile(backupdir)
    conn = sqlite3.connect(sqlitefile.name)
    
    messages = createMessages(conn)
    
    uploadMessages(messages)
    
      