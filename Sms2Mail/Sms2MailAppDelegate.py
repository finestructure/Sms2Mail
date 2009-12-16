# -*- coding: utf-8 -*-
#
#  Sms2MailAppDelegate.py
#  Sms2Mail
#
#  Created by Sven A. Schmidt on 30.11.09.
#  Copyright abstracture GmbH & Co. KG 2009. All rights reserved.
#

from Foundation import *
from AppKit import *
import sms2mail
import sqlite3

class Sms2MailAppDelegate(NSObject):

  devicePopup = objc.IBOutlet()
  productVersionLabel = objc.IBOutlet()
  lastBackupDateLabel = objc.IBOutlet()
  serialNumberLabel = objc.IBOutlet()
  messageCountLabel = objc.IBOutlet()
  messageView = objc.IBOutlet()
  
  productTypes = {'iPhone1,1':'Original iPhone',
                  'iPhone1,2':'iPhone 3G',
                  'iPhone2,1':'iPhone 3GS',
                  'iPod1,1':'Original iPod touch',
                  'iPod2,1':'2nd gen iPod touch',
                  'iPod3,1':'3rd gen iPod touch',
                  }

  messages = []


  def applicationDidFinishLaunching_(self, sender):
    self.devices = sms2mail.listDevices()
    self.devicePopup.removeAllItems()
    for dev in self.devices:
      try:
        productType = self.productTypes[dev['Product Type']]
      except KeyError:
        productType = dev['Product Type']
      title = u'%s – %s (%s)' % (dev['Device Name'], 
                                productType,
                                dev['Serial Number'])
      self.devicePopup.addItemWithTitle_(title)
    self.selectDevice(self.devices[0])


  @objc.IBAction
  def popupSelected_(self, sender):
    dev = self.devices[self.devicePopup.indexOfSelectedItem()]
    self.selectDevice(dev)
  
  
  def selectDevice(self, device):
    self.productVersionLabel.setObjectValue_(device['Product Version'])
    self.lastBackupDateLabel.setObjectValue_(device['Last Backup Date'])
    self.serialNumberLabel.setObjectValue_(device['Serial Number'])
    sqlitefile, _ = sms2mail.getSqliteFile(device['Backup Directory'])
    sqlitedb = sqlite3.connect(sqlitefile.name)
    self.messages = sms2mail.getMessages(sqlitedb, device['Phone Number'])
    if len(self.messages) == 1:
      s = '1 Message'
    else:
      s = '%d Messages' % len(self.messages)
    self.messageCountLabel.setStringValue_(s)
    self.sortMessageView()

  def numberOfRowsInTableView_(self, tableView):
    return len(self.messages)
  
  def tableView_objectValueForTableColumn_row_(self, tableView, tableColumn, row):
    msg = self.messages[row]
    if tableColumn.identifier() == 'From':
      return msg.sender
    elif tableColumn.identifier() == 'To':
      return msg.receiver
    elif tableColumn.identifier() == 'Date':
      return str(msg.date)
    elif tableColumn.identifier() == 'Message':
      return msg.body
  
  def tableView_sortDescriptorsDidChange_(self, tableView, oldDescriptors):
    self.sortMessageView()
  
  def sortMessageView(self):
    # only use first one for now
    try:
      desc = self.messageView.sortDescriptors()[0]
    except IndexError:
      # default sort order
      desc = NSSortDescriptor.alloc().initWithKey_ascending_('Date', False)
    if desc.ascending():
      sign = 1
    else:
      sign = -1
    if desc.key() == 'From':
      self.messages.sort(lambda x, y: sign*cmp(x.sender, y.sender))
    elif desc.key() == 'To':
      self.messages.sort(lambda x, y: sign*cmp(x.receiver, y.receiver))
    elif desc.key() == 'Date':
      self.messages.sort(lambda x, y: sign*cmp(x.date, y.date))
    else:
      return
    print 'first message:', self.messages[0]
    self.messageView.reloadData()
  


