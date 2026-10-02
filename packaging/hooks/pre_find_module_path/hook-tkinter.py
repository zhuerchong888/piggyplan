"""Keep tkinter discoverable when the host Tcl library has a relocated path."""


def pre_find_module_path(hook_api):
    # PiggyPlan supplies the Tcl/Tk binaries and data explicitly in build_exe.py.
    return None
