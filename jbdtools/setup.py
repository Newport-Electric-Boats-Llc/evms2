#!/usr/bin/env python

# BMS Tools
# Copyright (C) 2020 Eric Poulsen
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from setuptools import setup, find_packages

import os
import sys
import versioneer

if sys.version_info < (3, 6):
    raise RuntimeError('this package requires Python 3.6 or greater')

scriptFile = os.path.abspath(__file__)
scriptDir = os.path.dirname(scriptFile)

setup(
    name='bmstools',
    url='https://gitlab.com/MrSurly/bms-tools.git',
    project_urls={
        "Bug Tracker": "https://gitlab.com/bms-tools/bms-tools/-/issues",
    },
    author='Eric Poulsen',
    author_email='"Eric Poulsen" <eric@zyxod.com>',
    maintainer='Eric Poulsen',
    maintainer_email='"Eric Poulsen" <eric@zyxod.com>',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    install_requires=['pyserial~=3.4', 'xlsxwriter==1.3.7'],
    python_requires= '>= 3.6',
    ##data_files={'gui': ['gui/jbd_gui.py'] },
    extras_require = {
        'gui': ['wxPython~=4.1.1', 'pyinstaller']
    },
    license='Creative Commons Attribution-Noncommercial-Share Alike license',
    packages=find_packages(),
    entry_points = {
        'console_scripts': [
            'bmstools_jbd_gui=gui.jbd_gui:main' 
        ]
    },
    description="This package aims to provide open source tools for popular Battery Management Systems (BMS)",
    long_description="Please see [https://gitlab.com/MrSurly/bms-tools](https://gitlab.com/MrSurly/bms-tools)",
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux"
    ]
)

