import os
import sarge
import aeon

timer = aeon.Timer()

with timer("os.system"):
    cmd = ('tclsh', '/Users/fangohr/git/oommf/oommf/oommf.tcl', 'boxsi', '+fg', 'example-macrospin/example-macrospin.mif', '-exitondone', '1')
    cmd2 = " ".join(cmd)
    print("Command is '{}'".format(cmd2))
    os.system(cmd2)

print(timer.report())


with timer("sarge"):
    cmd = ('tclsh', '/Users/fangohr/git/oommf/oommf/oommf.tcl', 'boxsi', '+fg', 'example-macrospin/example-macrospin.mif', '-exitondone', '1')
    sarge.capture_both(cmd)

print(timer.report())
