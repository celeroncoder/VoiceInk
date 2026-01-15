#!/usr/bin/env python3
"""Run VoiceInk locally without installation (for development)"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from voiceink.main import main

if __name__ == '__main__':
    sys.exit(main())
