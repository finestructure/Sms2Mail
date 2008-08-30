
import sys
import os
from Foundation import *
import sqlite3
import datetime

mynumber = '+491712169993'

if len(sys.argv) < 2:
    #backupdir = os.environ['HOME'] + '/Library/Application Support/MobileSync/Backup'
    backupdir = os.environ['HOME'] + '/Downloads/Backup'
else:
    backupdir = sys.argv[1]


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

def writeSqliteFile(backupdir, fname='sms.db'):
    plist = getSmsPlist(backupdir)
    data = plist.objectForKey_('Data')
    data.writeToFile_atomically_(fname, True)

writeSqliteFile(backupdir)

sqlitefile = 'sms.db'
conn = sqlite3.connect(sqlitefile)

cur = conn.cursor()

groups = {}
cur.execute('select group_id, address from group_member order by address')
for g, a in cur.fetchall():
    if g not in groups.keys():
        groups[g] = [a]
    else:
        groups[g].append(a)

print groups

cur.execute('select address, date, text, flags, group_id from message order by date')
for a, d, t, f, g in cur.fetchall():
    #print a, d, t
    if a is None or t is None:
        continue
    subject = 'Conversation with %s (id %d)' % (', '.join(groups[g]), g)
    if f == 2: # to me
        sender = a
        recipient = mynumber
    else: # f == 3 typically
        sender = mynumber
        recipient = a
    date = datetime.datetime.fromtimestamp(d)
    
    print 'Subject:', subject
    print '\tFrom:', sender
    print '\tTo:', recipient
        
