#!/usr/bin/env python3
"""
Legacy entry point for Emm.
Redirects to the modular emm package.
"""

import sys
from pathlib import Path

# Ensure the root directory is in sys.path so we can import 'emm'
root_dir = Path(__file__).parent.parent.resolve()
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

try:
    from emm.cli import main
except ImportError as e:
    print(f"Error: Could not find 'emm' package. {e}")
    sys.exit(1)

if __name__ == "__main__":
    main()
