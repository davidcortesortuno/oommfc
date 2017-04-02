import datetime
import os
import sys
import time
import logging
c = logging.basicConfig(level=logging.DEBUG)


import sarge

from aeon import timer


class OOMMF:

    @timer.method
    def __init__(self, varname="OOMMFTCL", dockername="docker",
                 dockerimage="joommf/oommf", where=None):
        self.varname = varname
        self.dockername = dockername
        self.dockerimage = dockerimage
        self.statusdict = self.status(raise_exception=False)

    @timer.method
    def status(self, raise_exception=False, verbose=False):
        # OOMMF status on host
        cmd = ("tclsh", os.getenv(self.varname, "wrong"), "boxsi",
               "+fg", "+version", "-exitondone", "1")
        try:
            poommf = self._run_cmd(cmd)
            returncode = poommf.returncode
        except FileNotFoundError:
            returncode = 1
        if returncode:
            host = False
            if verbose:
                oommfpath = os.getenv(self.varname)
                if oommfpath is None:
                    print("Cannot find {} path.".format(self.varname))
                elif not os.path.isfile(oommfpath):
                    print("{} path {} set to a non-existing "
                          "file.".format(self.varname, oommfpath))
                else:
                    print("{} path {} set to an existing "
                          "file.".format(self.varname, oommfpath))
                    print("Something wrong with OOMMF installation.")
        else:
            host = True

        # Docker status
        cmd = (self.dockername, "images")
        try:
            pdocker = self._run_cmd(cmd)
            returncode = pdocker.returncode
        except FileNotFoundError:
            returncode = 1

        if returncode:
            docker = False
            if verbose:
                print("Docker not installed/active.")
        else:
            docker = True

        # Raise exception if required
        if not (host or docker) and raise_exception:
            raise EnvironmentError("OOMMF and docker not found.")

        return {"host": host, "docker": docker}


    @timer.method
    def _check_return_value(self, ret):

        # there must be at least one ...
        assert len(ret.commands) > 0, "No commands to report?"

        # then take the last one:
        command = ret.commands[-1]

        if command.returncode is not 0:
            stderr = command.stderr.read()
            stdout = command.stdout.read()
            cmdstr = " ".join(command.args)
            print("Error when executing:")
            print("\tcommand: {}".format(cmdstr))
            print("\tstdout: {}".format(stdout))
            print("\tstderr: {}".format(stderr))
            print("\n")

        return ret

    #@timer.method
    def call(self, argstr, where=None):
        logging.debug("Call starts")
        #with self.timer("call"):
            # print day and time at which we start calling OOMMF (useful
            # for longer runs)
        x = datetime.datetime.now()
        timestamp = "{}/{}/{} {}:{}".format(x.year, x.month, x.day,
                                            x.hour, x.minute)
        print("{}: Calling OOMMF ({}) ... ".format(timestamp, argstr), end='')

        # measure execution time of OOMMF
        tic = time.time()
        where = self._where_to_run(where=where)
        if where == "host":
            val = self._call_host(argstr=argstr)
        elif where == "docker":
            val = self._call_docker(argstr=argstr)

        toc = time.time()
        seconds = "[{:0.1f}s]".format(toc - tic)
        print(seconds)
        logging.debug("oommf::call execution took {} seconds".format(seconds))
        # check exit code
        val = self._check_return_value(val)

        if val.returncode is not 0:
            raise RuntimeError("Some problem calling OOMMF.")

        logging.debug("oommf::call return value is {}".format(val.returncode))
        logging.debug("oommf::call return val is {}".format(val))

        return val


    @timer.method
    def version(self, where=None):
        where = self._where_to_run(where=where)
        p = self.call(argstr="+version", where=where)
        return p.stderr.text.split("oommf.tcl")[-1].strip()

    @timer.method
    def platform(self, where=None):
        where = self._where_to_run(where=where)
        p = self.call(argstr="+platform", where=where)
        return p.stderr.text

    @timer.method
    def _where_to_run(self, where):
        if where is None:
            if self.statusdict["host"]:
                return "host"
            else:
                return "docker"
        else:
            return where

    @timer.method
    def _call_host(self, argstr):
        oommfpath = os.getenv(self.varname, None)
        cmd = ("tclsh", oommfpath, "boxsi", "+fg",
               argstr, "-exitondone", "1")
        return self._run_cmd(cmd)

    @timer.method
    def _call_docker(self, argstr):
        cmd = "{} pull {}".format(self.dockername, self.dockerimage)
        self._run_cmd(cmd)
        cmd = ("{} run -v {}:/io {} /bin/bash -c \"tclsh "
               "/usr/local/oommf/oommf/oommf.tcl boxsi +fg {} "
               "-exitondone 1\"").format(self.dockername, os.getcwd(),
                                         self.dockerimage, argstr)
        return self._run_cmd(cmd)

    def _run_cmd(self, cmd):
        start = time.time()
        def report_time():
            calltime = time.time()-start
            print("_run_cmd: took {:.1f}s to call '{}'".format(calltime, cmd))
            return calltime
        if sys.platform in ("linux", "darwin"):  # Linux and MacOs
            ret = sarge.capture_both(cmd)
            report_time()
            return ret
        elif sys.platform.startswith("win"):
            return sarge.run(cmd)
        else:
            msg = ("Cannot handle platform '{}' - please report to "
                   "developers").format(sys.platform)  # pragma: no cover
            raise NotImplementedError(msg)

    @timer.method
    def kill(self, targets=('all',), where=None):
        where = self._where_to_run(where)
        if where == 'host':
            oommfpath = os.getenv(self.varname, None)
            sarge.run(("tclsh", oommfpath, "killoommf") + targets)
