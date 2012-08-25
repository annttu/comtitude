#!/usr/bin/env python
# encoding: utf-8

## Simple OS X system tray app
## Creates "C" system tray icon and menu for it
## Antti 'Annttu' Jaakkola

from Foundation import *
from AppKit import *
from PyObjCTools import AppHelper
from comtitude import Comtitude
import os

start_time = NSDate.date()

class MyApplicationAppDelegate(NSObject):

    state = 'idle'

    def applicationDidFinishLaunching_(self, sender):

        self.statusItem = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        self.statusImage = NSImage.alloc()
        icon = os.path.join(os.path.dirname(os.path.abspath(__file__)),'icons/comtitude-16.png')
        self.statusImage.initWithContentsOfFile_(icon)
        #self.statusItem.setTitle_(u"C")
        self.statusItem.setImage_(self.statusImage)
        self.statusItem.setToolTip_('Comtitude')
        self.statusItem.setHighlightMode_(TRUE)
        self.statusItem.setEnabled_(TRUE)

        # Menu
        self.menu = NSMenu.alloc().init()
        self.coordinate = NSMenuItem.alloc().init()
        self.coordinate.setTitle_('Location')
        self.coordinate.setToolTip_('Location or Adderss')
        self.coordinate.setKeyEquivalent_('t')
        self.menu.addItem_(self.coordinate)
        self.time = NSMenuItem.alloc().init()
        self.time.setTitle_('Time')
        self.time.setKeyEquivalent_('T')
        self.time.setToolTip_('Time last updated')
        self.time.setAlternate_(TRUE)
        self.menu.addItem_(self.time)
        menuitem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_('Sync...', 'sync:', '')
        self.menu.addItem_(menuitem)
        menuitem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_('Quit', 'terminate:', '')
        self.menu.addItem_(menuitem)

        self.statusItem.setMenu_(self.menu)

        # initialize comtitude
        self.comtitude = Comtitude()

        # Get the timer going
        self.timer = NSTimer.alloc().initWithFireDate_interval_target_selector_userInfo_repeats_(
                            start_time, float(self.comtitude.delay), self, 'sync:', None, True)
        NSRunLoop.currentRunLoop().addTimer_forMode_(self.timer, NSDefaultRunLoopMode)
        self.timer.fire()

        NSLog("Comtitude started!.")

    def sync_(self, notification):
        self.comtitude._update()
        self.coordinate.setTitle_('%s' % self.comtitude.status())
        if self.comtitude.last:
            self.time.setTitle_('%s' % self.comtitude.last_updated())

def hide_from_dock():
    """hide icon from dock"""
    NSApplicationActivationPolicyRegular = 0
    NSApplicationActivationPolicyAccessory = 1
    NSApplicationActivationPolicyProhibited = 2
    NSApp.setActivationPolicy_(NSApplicationActivationPolicyProhibited)

if __name__ == "__main__":
    try:
        app = NSApplication.sharedApplication()
        app.hide_(TRUE)
        delegate = MyApplicationAppDelegate.alloc().init()
        app.setDelegate_(delegate)
        hide_from_dock()
        AppHelper.runEventLoop()
    except KeyboardInterrupt:
        delegate.terminate_()
        AppHelper.stopEventLoop()
        pass
