import sys
import time
import pexpect
import subprocess as subp
from SCAutolib import log


class VirtCard:
    def __init__(self):
        log.debug("Smart card initialized")

    def __enter__(self):
        return self

    def __exit__(self, except_type, except_value, except_trace):
        self.remove()

    def remove(self):
        subp.run(["systemctl", "stop", "virt_cacard.service"])
        log.debug("Smart card removed")

    def insert(self):
        subp.run(["systemctl", "start", "virt_cacard.service"])
        time.sleep(2)
        log.debug("Smart card inserted")

    def enroll(self):
        log.debug("Smart card enrolled")

    def run_cmd(self, cmd: str, expect: str = None, pin: bool = True, passwd: str = None, shell=None):
        try:
            if shell is None:
                shell = pexpect.spawn(cmd, encoding='utf-8')
            shell.logfile = sys.stdout

            if passwd is not None:
                pattern = "PIN for " if pin else "Password"
                time.sleep(1)
                out = shell.expect([pexpect.TIMEOUT, pattern], timeout=10)

                if out != 1:
                    if out == 0:
                        log.error("Timed out on passsword / PIN waiting")
                    expect = pattern

                    raise pexpect.exceptions.EOF(f"Pattern '{pattern}' is not "
                                                 f"found in the output.")
                shell.sendline(passwd)

            if expect is not None:
                out = shell.expect([pexpect.TIMEOUT, expect], timeout=20)

                if out != 1:
                    if out == 0:
                        log.error("Time out")
                    raise pexpect.exceptions.EOF(f"Pattern '{expect}' is not "
                                                 f"found in the output.")

        except pexpect.exceptions.EOF as e:
            log.error(
                f"Pattern '{expect}' not found in output.\n"
                f"Output:\n{str(shell.before)}")
            raise e
        except Exception as e:
            log.error(f"Unexpected exception: {str(e)}")
            raise e
        return shell
