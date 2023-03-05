# BMS Tools

## Screenshots

<a href="doc_img/windows-info-screenshot.png"><img src="doc_img/windows-info-screenshot.png" width="250"/></a><br>
Windows version, cell info tab.

[More Screenhots](SCREENSHOTS.md)


## Purpose
This repository aims to provide open source tools for popular Battery Management Systems (BMS).  

## Support
Currently it only supports the [JBD](https://www.lithiumbatterypcb.com/) BMS.

I've compiled some [JBD register documentation](JBD_REGISTER_MAP.md), and at the time of this writing the most complete that I could find.

### Planned feature support for JBD BMS

<table>
  <tr>
    <th>Feature</th><th>Support</th>
  </tr>
  <tr>
    <td>Cell / device info</td><td bgcolor="green"><font color="white">Full support</text></td>
  </tr>
  <tr>
    <td>EEPROM Settings</td><td bgcolor="green"><font color="white">Full support</font></td>
  </tr>
  <tr>
    <td>Calibration</td><td bgcolor="green"><font color="white">Full support</font></td>
  </tr>
  <tr>
    <td>MOS Control, Remaining capacity edit, balance control</td><td bgcolor="green"><font color="white">Full support</font></td>
  </tr>
  <tr>
    <td>Logging</td><td bgcolor="green"><font color="white">Full support</font></td>
  </tr>
  <tr>
    <td>Graphing</td><td bgcolor="#808080"><font color="white">Planned</font></td>
  </tr>
  <tr>
    <td>BLE Support</td><td bgcolor="orange"><font color="black">Investigating</font></td>
  </tr>
  <tr>
    <td>Firmware update</td><td bgcolor="red"><font color="black">Not planned</text></td>
  </tr>
</table>

## Code

Currently provided:

* Backend Python library 
* Frontent GUI App

Planned:

* Command line app

### Changelog
[Changelog](CHANGELOG.md)

## Installation

### Backend Library

`pip install .`

### GUI Build

#### Prerequisites (Debian systems e.g. Raspi):

* `sudo apt-get install libgtk3-dev`

While the GUI itself is wxpython and doesn't technically _need_ to be built, but for distribution 
 [pyinstaller](https://www.pyinstaller.org/) is used to build a distributable executable.

1. `pip install .[gui]`
1. make








