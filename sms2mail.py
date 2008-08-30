
import sys
import os
from Foundation import *
import sqlite3
import datetime

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

#writeSqliteFile(backupdir)

sqlitefile = 'sms.db'
conn = sqlite3.connect(sqlitefile)

cur = conn.cursor()
cur.execute('select address, date, text from message')
for a, d, t in cur.fetchall():
    print a, d, t
    number = '1712169993'
    if a is not None and number in a:
        d = datetime.datetime.fromtimestamp(d)
        #print d
        #print t
        
