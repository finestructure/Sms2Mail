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
  
  productTypes = {'iPhone1,1':'Original iPhone',
                  'iPhone1,2':'iPhone 3G',
                  'iPhone2,1':'iPhone 3GS',
                  'iPod1,1':'Original iPod touch',
                  'iPod2,1':'2nd gen iPod touch',
                  'iPod3,1':'3rd gen iPod touch',
                  }

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
    sqlitefile, fname = sms2mail.getSqliteFile(device['Backup Directory'])
    print '... found:', fname
    print 'Connecting with sqlite3 ...'
    sqlitedb = sqlite3.connect(sqlitefile.name)
    print '... successful.'
    print 'Getting messages from sqlite db ...'
    messages = sms2mail.getMessages(sqlitedb, device['Phone Number'])
    print '... found %d messages' % len(messages)

  
