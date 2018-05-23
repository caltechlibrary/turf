#!/usr/bin/env python3
# =============================================================================
# @file    turf_debug.py
# @brief   Run turf with debug enabled
# @author  Michael Hucka <mhucka@caltech.edu>
# @license Please see the file named LICENSE in the project directory
# @website https://github.com/caltechlibrary/turf
# =============================================================================

import os
import sys
import plac

# Allow this program to be executed directly from the 'tests' directory.
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import logging
logging.basicConfig(level=logging.DEBUG, format='')

import turf
from turf.__main__ import main as main
plac.call(main)
