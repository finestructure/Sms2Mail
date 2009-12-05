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

  tf = objc.IBOutlet()
  productTypes = {'iPhone1,1':'Original iPhone',
                  'iPhone1,2':'iPhone 3G',
                  'iPhone2,1':'iPhone 3GS',
                  'iPod1,1':'Original iPod touch',
                  'iPod2,1':'iPod touch (2nd gen)',
                  'iPod3,1':'iPod touch (3rd gen)',
                  }

  def applicationDidFinishLaunching_(self, sender):
    self.devices = sms2mail.listDevices()
    self.tf.removeAllItems()
    for dev in self.devices:
      try:
        productType = self.productTypes[dev['Product Type']]
      except KeyError:
        productType = dev['Product Type']
      title = '%s (%s - %s)' % (dev['Device Name'], 
                                dev['Product Version'],
                                productType)
      self.tf.addItemWithTitle_(title)
      
  @objc.IBAction
  def buttonPressed_(self, sender):
    backupdir = self.devices[self.tf.indexOfSelectedItem()]['Backup Directory']
    NSLog(backupdir)
