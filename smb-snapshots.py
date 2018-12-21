#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
import argparse
import configparser
import datetime as date
import logging
import os
import re
import shutil
import subprocess
import sys
from subprocess import CompletedProcess
from typing import List, Tuple, Union


class SmbSnapshots:

    def __init__(self, dry_run, snap_count, pre_exec, post_exec, shares, shares_root, snap_root) -> None:
        logging.info("Starting smb-snapshots")

        self._cmd_failed = False

        self._snap_folder = date.datetime.utcnow().strftime("@GMT-%Y.%m.%d-%H.%M.%S")

        self._dry_run = dry_run
        self._snap_count = snap_count
        self._pre_exec = pre_exec
        self._post_exec = post_exec
        self._shares = shares
        self._shares_root = shares_root
        self._snap_root = snap_root

    def _run_command(self, cmd) -> bool:
        if isinstance(cmd, str):
            logging.info("Command: %s", cmd)
            if not self._dry_run:
                res_s = subprocess.getstatusoutput(cmd)
                if res_s[0] != 0:
                    self._cmd_failed = True
                    logging.error("Last command failed!\n%s", res_s[1])
                    return False
            return True
        elif isinstance(cmd, list):
            logging.info("Command: %s", " ".join(cmd))
            if not self._dry_run:
                res_l = subprocess.run(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                if res_l.returncode != 0:
                    self._cmd_failed = True
                    logging.error("Last command failed!\n%s",
                                  res_l.stdout.decode("utf-8"))
                    return False
            return True
        raise ValueError("Invalid command type!")

    def do_snapshot(self) -> bool:
        if self._pre_exec:
            if not self._run_command(self._pre_exec):
                logging.error("Could not run PRE_EXEC command!")
                return False

        for share_name in self._shares:
            share = os.path.normpath(
                "{}/{}".format(self._shares_root, share_name))
            snap = os.path.normpath(
                "{}/{}".format(self._snap_root, share_name))
            dest = os.path.normpath("{}/{}".format(snap, self._snap_folder))

            if not os.path.exists(share):
                logging.error("Share %s not found! Ignoring...", share)
            else:
                snaps: List[str] = []
                first_snapshot = not os.path.exists(snap)
                if first_snapshot:
                    # We don't have a snapshot root dir for this share, create it
                    if not self._dry_run:
                        os.mkdir(snap)
                else:
                    # List all snapshots we have
                    snaps = [f for f in os.listdir(snap) if re.match(
                        r"@GMT-[0-9]{4}\.[0-9]{2}\.[0-9]{2}-[0-9]{2}\.[0-9]{2}\.[0-9]{2}", f)]
                    snaps.sort()

                source = share  # The default source is the share itself.

                # If we have snapshots, the source will be the last one
                if len(snaps) > 0:
                    source = os.path.normpath("{}/{}".format(snap, snaps[-1]))

                if first_snapshot:
                    # As this is the first snapshot, we must copy the files instead linking
                    command = ["cp", "-a",
                               "{}/.".format(source), "{}/".format(dest)]
                else:
                    command = [
                        "rsync", "-aAX", "--link-dest={}".format(source), "{}/".format(share), dest]

                if not self._run_command(command):
                    logging.error(
                        "Sync failed, will not remove old snapshots.")
                else:
                    # Remove old snapshots
                    logging.debug("Snapshots Count: %s, max: %s",
                                  len(snaps), self._snap_count)
                    snaps = snaps[:len(snaps) - self._snap_count]
                    for snapRm in snaps:
                        path = os.path.normpath("{}/{}".format(snap, snapRm))
                        logging.info("Removing old snapshot '%s'.", path)
                        if not self._dry_run:
                            shutil.rmtree(path)

        if self._post_exec:
            self._run_command(self._post_exec)

        if self._cmd_failed:
            return False

        return True


_CFG_FILE = "/etc/smb-snapshot.conf"
_LOG_FILE = "/var/log/smb-snapshot.log"


def main():
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Create/Manage SMB snapshots", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-c", "--cfg-file",
                        help="Configuration file", default=_CFG_FILE)
    parser.add_argument("-l", "--log-file", help="Log file", default=_LOG_FILE)
    parser.add_argument(
        "--dry-run", help="Do not make changes", action="store_true")
    parser.add_argument("-v", "--verbose", help="Verbose", action="store_true")
    args = parser.parse_args()

    # Parse Configuration File
    if not os.path.exists(args.cfg_file):
        print("Configuration file not found! Default location: {}.".format(
            _CFG_FILE), file=sys.stderr)
        print("""[Config]
    # How many snapshots to keep(Default: 210)
    SNAP_COUNT = 100

[Cmd]
    # Command that will be executed before snapshots
    PRE_EXEC = /bin/mount -o remount,rw /srv/snapshots
    # Command that will be executed after snapshots(Even after a failure)
    POST_EXEC = /bin/mount -o remount,ro /srv/snapshots

[Directories]
    # Root folder to shares
    SHARES_ROOT = /srv/shares
    # Snapshots root folder
    SNAP_ROOT = /srv/snapshots
    # Shares to create snapshots(Relative to SHARES_ROOT, comma separated)
    SHARES = My Share 1,My Share 2,ShareN""", file=sys.stderr)
        sys.exit(1)

    config = configparser.ConfigParser()
    config.read(args.cfg_file)
    try:
        # Config
        snap_count = int(config["Config"].get("SNAP_COUNT", 210))
        # Cmds
        pre_exec = config["Cmd"].get("PRE_EXEC", "")
        post_exec = config["Cmd"].get("POST_EXEC", "")
        # Directories
        shares = [entry.strip()
                  for entry in config["Directories"]["SHARES"].split(",")]
        shares_root = config["Directories"]["SHARES_ROOT"]
        snap_root = config["Directories"]["SNAP_ROOT"]
    except KeyError as error:
        print("Key {} missing in configuration file!".format(
            error), file=sys.stderr)
        sys.exit(2)

    if not os.path.exists(shares_root):
        print("SHARES_ROOT '{}' not found!".format(
            shares_root), file=sys.stderr)
        sys.exit(3)

    # Setup Logging
    class InfoFilter(logging.Filter):

        def filter(self, rec) -> bool:
            return rec.levelno in (logging.DEBUG, logging.INFO)

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.DEBUG if args.verbose else logging.INFO,
        handlers=[logging.FileHandler(args.log_file)])
    logger = logging.getLogger()
    handlerOut = logging.StreamHandler(sys.stdout)
    handlerOut.setLevel(logger.level)
    handlerOut.addFilter(InfoFilter())
    handlerErr = logging.StreamHandler()
    handlerErr.setLevel(logging.WARNING)
    logger.addHandler(handlerOut)
    logger.addHandler(handlerErr)

    # Starting
    if SmbSnapshots(args.dry_run, snap_count, pre_exec, post_exec, shares, shares_root, snap_root).do_snapshot():
        logging.info("smb-snapshots finished!")
        sys.exit(0)

    print("smb-snapshots finished with errors!", file=sys.stderr)
    sys.exit(4)


if __name__ == "__main__":
    main()
