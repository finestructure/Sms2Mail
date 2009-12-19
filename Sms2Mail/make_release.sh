#!/bin/sh
xcodebuild -configuration Release
zip -r Sms2Mail.app.zip build/Release/Sms2Mail.app
