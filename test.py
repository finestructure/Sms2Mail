# -*- coding: utf-8 -*-
import os
from Foundation import *
import StringIO
import tempfile
from time import localtime
import ConfigParser
import imaplib
import pickle
import sqlite3
import datetime, time
import hashlib
import email
from email.message import Message

import sms2mail
from sms2mail import lookupName, getGroups, getSqliteFile, getMessages, createMessage

config_filename = os.path.expanduser('~/.sms2mail.conf')
cache_filename = os.path.expanduser('~/.sms2mail.cache')




if __name__ == '__main__':
  backupdir = os.path.expanduser('~/Library/Application Support/'
                                 'MobileSync/Backup')
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
  
  M = imaplib.IMAP4_SSL(host=host, port=port)
  M.login(user, password)    

  #sqlitefile, fname = getSqliteFile(backupdir)
  #sqlitedb = sqlite3.connect(sqlitefile.name)

  msg = createMessage(u'me äöü', u'them äöü', u'subject äüö', 1194623448, 'sms_id', u'body äü')
  print '----------------\n', msg
  res, _ = M.append('Inbox', None, time.localtime(), msg.as_string())
  print res
  
  