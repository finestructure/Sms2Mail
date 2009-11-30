#
#  main.py
#  Sms2Mail
#
#  Created by Sven A. Schmidt on 30.11.09.
#  Copyright abstracture GmbH & Co. KG 2009. All rights reserved.
#

#import modules required by application
import objc
import Foundation
import AppKit

from PyObjCTools import AppHelper

# import modules containing classes required to start application and load MainMenu.nib
import Sms2MailAppDelegate

# pass control to AppKit
AppHelper.runEventLoop()
