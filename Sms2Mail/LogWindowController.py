#
#  LogWindowController.py
#  Sms2Mail
#
#  Created by Sven A. Schmidt on 17.12.09.
#  Copyright (c) 2009 abstracture GmbH & Co. KG. All rights reserved.
#

from objc import YES, NO, IBAction, IBOutlet
from Foundation import *
from AppKit import *

class LogWindowController(NSWindowController):
    
  textField = objc.IBOutlet()
  
  def windowFrameAutosaveName(self):
    return 'LogWindow'
    