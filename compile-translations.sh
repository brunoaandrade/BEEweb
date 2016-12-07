#!/usr/bin/env bash

# German language
msgfmt translations/de/LC_MESSAGES/messages.po --output-file translations/de/LC_MESSAGES/messages.mo
msgfmt src/octoprint/translations/de/LC_MESSAGES/messages.po --output-file src/octoprint/translations/de/LC_MESSAGES/messages.mo
