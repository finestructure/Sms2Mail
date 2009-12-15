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

class Sms2MailAppDelegate(NSObject):

  devicePopup = objc.IBOutlet()
  productVersionLabel = objc.IBOutlet()
  lastBackupDateLabel = objc.IBOutlet()
  productTypes = {'iPhone1,1':'Original iPhone',
                  'iPhone1,2':'iPhone 3G',
                  'iPhone2,1':'iPhone 3GS',
                  'iPod1,1':'Original iPod touch',
                  'iPod2,1':'iPod touch (2nd gen)',
                  'iPod3,1':'iPod touch (3rd gen)',
                  }

  def applicationDidFinishLaunching_(self, sender):
    self.devices = sms2mail.listDevices()
    self.devicePopup.removeAllItems()
    for dev in self.devices:
      print 'dev:', dev
      try:
        productType = self.productTypes[dev['Product Type']]
      except KeyError:
        productType = dev['Product Type']
      title = '%s (%s)' % (dev['Device Name'], productType)
      self.devicePopup.addItemWithTitle_(title)
    self.productVersionLabel.setObjectValue_(self.devices[0]['Product Version'])
    self.lastBackupDateLabel.setObjectValue_(self.devices[0]['Last Backup Date'])
      
  @objc.IBAction
  def popupSelected_(self, sender):
    NSLog('popup selected: ' + str(sender.indexOfSelectedItem()))
    dev = self.devices[self.devicePopup.indexOfSelectedItem()]
    self.productVersionLabel.setValue_(dev['Product Version'])
    self.lastBackupDateLabel.setValue_(dev['Last Backup Date'])
    