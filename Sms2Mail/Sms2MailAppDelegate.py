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
    NSLog("Application did finish launching.")

  @objc.IBAction
  def buttonPressed_(self, sender):
    sqlitefile, fname = sms2mail.getSqliteFile(sms2mail.backupdir)
    self.tf.setStringValue_(fname)