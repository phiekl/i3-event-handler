# Copyright 2023 Philip Eklöf
#
# SPDX-License-Identifier: MIT

from setuptools import setup

setup(
    name="i3-event-handler",
    version="0.1",
    description="A daemon-ish library/tool to handle i3 window events.",
    author="Philip Eklöf",
    author_email="phi@pxy.se",
    packages=["i3eventhandler"],
    entry_points={"console_scripts": ["i3-event-handler=i3eventhandler.cli:main"]},
    install_requires=["i3ipc"],
)
