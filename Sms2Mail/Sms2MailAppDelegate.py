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

  def applicationDidFinishLaunching_(self, sender):
    self.devices = sms2mail.listDevices()
    self.tf.removeAllItems()
    for dev in self.devices:
      title = '%s (%s - %s)' % (dev['Device Name'], 
                                dev['Product Version'],
                                dev['Product Type'])
      self.tf.addItemWithTitle_(title)
      
  @objc.IBAction
  def buttonPressed_(self, sender):
    backupdir = self.devices[self.tf.indexOfSelectedItem()]['Backup Directory']
    NSLog(backupdir)
