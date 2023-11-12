# Copyright 2023 Philip Eklöf
#
# SPDX-License-Identifier: MIT

import argparse
import logging
import pathlib
import sys

from i3eventhandler import EventHandler, EventHandlerError


def arg_parse():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-c",
        "--config-file",
        default=pathlib.Path.home() / ".config/i3/event_handler.json",
        help="configuration file path",
        type=pathlib.Path,
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        default=False,
        help="decrease log level to WARNING",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="increase the verbosity level",
    )

    return parser.parse_args()


def main():
    opts = arg_parse()

    log_level = logging.INFO
    if opts.quiet:
        log_level = logging.WARNING
    elif opts.verbose > 0:
        log_level = logging.DEBUG

    logging.basicConfig(format="%(levelname)s: %(name)s: %(message)s", level=log_level)
    logging.getLogger("i3ipc").setLevel(logging.WARNING)
    if opts.verbose > 0:
        logging.getLogger("i3ipc").setLevel(logging.INFO)

    try:
        EventHandler(opts.config_file).main()
    except EventHandlerError as e:
        raise SystemExit(f"ERROR: i3eventhandler: {e}") from e
    except KeyboardInterrupt:
        print("", file=sys.stderr)
        raise SystemExit(130) from None
