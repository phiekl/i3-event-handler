# Copyright 2023 Philip Eklöf
#
# SPDX-License-Identifier: MIT

import json
import logging
import pathlib
import re

import i3ipc

from .exceptions import EventHandlerError

logger = logging.getLogger("i3eventhandler")


class EventHandler:
    def __init__(self, config_file=None):
        self.config_file = pathlib.Path(config_file)
        self.config = None
        self.ipc = None

        self._connect()
        self._config_verify()

    def _config_load(self):
        if not self.config_file.is_file():
            raise EventHandlerError(f"Configuration file not found: {self.config_file}")

        with self.config_file.open("rb") as fh:
            try:
                self.config = json.load(fh)
            except json.JSONDecodeError as e:
                raise EventHandlerError(
                    f"Invalid JSON file: {self.config_file}: %{e}"
                ) from e

    # pylint: disable=too-many-branches
    def _config_verify(self):
        if not self.config:
            self._config_load()

        p = f"Configuration file ({self.config_file})"

        if not isinstance(self.config, list):
            raise EventHandlerError(f"{p} should contain an array")

        for n, rule in enumerate(self.config):
            if "_matches" not in rule:
                raise EventHandlerError(f"{p}: .[{n}]._matches not found")
            if not isinstance(rule["_matches"], list):
                raise EventHandlerError(f"{p}: .[{n}]._matches is not an array")
            if not rule["_matches"]:
                raise EventHandlerError(f"{p}: .[{n}]._matches is empty")

            for n2, item in enumerate(rule["_matches"]):
                if not isinstance(item, list):
                    raise EventHandlerError(
                        f"{p}: .[{n}]._matches[{n2}] is not an array"
                    )
                if len(item) != 2:
                    raise EventHandlerError(
                        f"{p}: .[{n}]._matches[{n2}] must contain two items"
                    )
                if item[0] not in ("class", "instance", "title"):
                    raise EventHandlerError(
                        f"{p}: .[{n}]._matches[{n2}][0] ({item[0]}) must be"
                        f" set to one of 'class', 'instance' or 'title'"
                    )
                if not item[1]:
                    raise EventHandlerError(f"{p}: .[{n}]._matches[{n2}][1] is empty")

                try:
                    re.compile(item[1])
                except re.error as e:
                    raise EventHandlerError(
                        f"{p}: .[{n}]._matches[{n2}][1] () is not a valid regex: {e}"
                    ) from e

            if "mark" in rule:
                if not isinstance(rule["mark"], str):
                    raise EventHandlerError(f"{p}: .[{n}].mark is not a string")
                if not rule["mark"]:
                    raise EventHandlerError(f"{p}: .[{n}].mark is empty")
            else:
                rule["mark"] = None

            if "on_new" in rule:
                if not isinstance(rule["on_new"], list):
                    raise EventHandlerError(f"{p}: .[{n}].on_new is not an array")

                for n2, item in enumerate(rule["on_new"]):
                    if not isinstance(item, str):
                        raise EventHandlerError(
                            f"{p}: .[{n}].on_new[{n2}] is not a string"
                        )
                    if not item:
                        raise EventHandlerError(f"{p}: .[{n}].on_new[{n2}] is empty")
            else:
                rule["on_new"] = []

        logger.info(
            "successfully read %s rules from file: %s",
            len(self.config),
            self.config_file,
        )

    def _connect(self):
        try:
            self.ipc = i3ipc.Connection(auto_reconnect=True)
        except FileNotFoundError as e:
            raise EventHandlerError(
                "Failed to connect to i3: The I3SOCK environment variable seems "
                "to have been set, and it might be faulty"
            ) from e

        except Exception as e:
            raise EventHandlerError(f"Failed to connect to i3: {e}") from e

    def _event_handler(self, _, evt):
        con = evt.container

        logger.info(
            "event: change(%s) id(%s) class(%s) instance(%s) title(%s)",
            evt.change,
            con.id,
            con.window_class,
            con.window_instance,
            con.window_title,
        )

        rule = self._window_match(
            {
                "class": con.window_class,
                "instance": con.window_instance,
                "title": con.window_title,
            }
        )

        if not rule:
            logger.info("found no matching rule for window")
            return

        logger.info("found matching rule for window")

        if evt.change == "new":
            if rule["mark"]:
                marked = self.ipc.get_tree().find_marked(
                    "^" + re.escape(rule["mark"]) + "$"
                )
                if marked:
                    logger.info(
                        "not marking window since another window is already marked as '%s'",
                        rule["mark"],
                    )
                else:
                    logger.info("marking window as '%s'.", rule["mark"])
                    con.command(f"mark --replace {rule['mark']}")

            for cmd in rule["on_new"]:
                logger.info("sending window command: %s", cmd)
                con.command(cmd)

    def _window_match(self, matches):
        for rule in self.config:
            matching = True
            for match_type, match_regex in rule["_matches"]:
                if not re.match(match_regex, matches[match_type]):
                    matching = False

            if matching:
                return rule

        return None

    def main(self):
        self.ipc.on(i3ipc.Event.WINDOW_NEW, self._event_handler)
        self.ipc.main()
