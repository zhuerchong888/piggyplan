"""Point the frozen process at its bundled Tcl/Tk script directories."""

import os
import sys


bundle_root = getattr(sys, "_MEIPASS", "")
if bundle_root:
    os.environ["TK_LIBRARY"] = os.path.join(bundle_root, "_tk_data")
