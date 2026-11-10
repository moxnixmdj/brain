"""Does the hand-written lexicon transfer, or did it memorise the probes it was written on?

The dictionary was written AFTER reading failures on the original probe set. That is the
definition of a tuned parameter, and a tuned parameter's score on its own tuning set means
nothing. So: a second probe set, written fresh, deliberately avoiding the words in
VERB_SYNONYMS and INFLECTIONS. If FULL holds up on these, the lexicon captured something
about how people phrase actions. If it collapses toward NO_DICT, the 84.4% was memorisation.

Every held-out probe below uses a verb that does NOT appear in the synonym table anywhere.
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

HELDOUT = {
    # skill key : a request using vocabulary absent from VERB_SYNONYMS
    "file_rename": "alter the label on this file",
    "file_delete": "consign this file to oblivion",
    "file_copy": "replicate the file",
    "file_move": "transport the file elsewhere",
    "file_compress": "shrink the file down",
    "file_open": "surface the file for me",
    "file_share": "distribute the file to a colleague",
    "file_lock": "prohibit changes to the file",
    "text_bold": "thicken this word",
    "text_italic": "incline these letters",
    "text_underline": "score a line under this",
    "text_search": "locate a word in this paragraph",
    "text_replace": "substitute one word for another",
    "text_count": "enumerate the words here",
    "text_translate": "render this into french",
    "text_summarise": "condense this",
    "web_navigate": "visit example dot com",
    "web_reload": "redraw what is on screen",
    "web_bookmark": "pin this page for later",
    "web_scroll": "descend the page",
    "web_fill": "enter my details into the boxes",
    "web_submit": "dispatch the form",
    "web_screenshot": "photograph what the screen shows",
    "web_download": "pull this page onto my computer",
    "data_sort": "arrange the rows in sequence",
    "data_filter": "narrow down which rows appear",
    "data_group": "cluster rows that belong together",
    "data_pivot": "transpose rows into columns",
    "data_export": "dump the table to a file",
    "data_import": "load a table from a file",
    "data_dedupe": "strip out duplicate rows",
    "data_join": "merge two tables on a key",
    "media_crop": "shave the edges off this picture",
    "media_resize": "enlarge this picture",
    "media_rotate": "twist this picture sideways",
    "media_brightness": "brighten this picture",
    "media_convert": "reformat this picture",
    "media_watermark": "brand the picture with my name",
    "media_trim": "shorten the clip",
    "media_mute": "deaden the sound",
    "system_install": "provision a library on this machine",
    "system_disk": "how much room is left on the drive",
    "system_ps": "enumerate what is running",
    "system_kill": "terminate that running program",
    "system_start": "raise the server",
    "system_stop": "lower the server",
    "system_logs": "what did the server record",
    "system_env": "declare a variable for the shell",
    "comms_send": "dispatch this to the team",
    "comms_reply": "respond to this message",
    "comms_forward": "relay this message onward",
    "comms_archive": "store this message away",
    "comms_schedule": "insert a meeting into the calendar",
    "comms_decline": "refuse the invitation",
    "comms_post": "compose in the channel",
    "comms_mention": "summon someone in the chat",
    "deploy_staging": "promote it to the test servers",
    "deploy_prod": "promote it to the live servers",
    "deploy_rollback": "revert the last release",
    "deploy_tag": "label this version",
    "deploy_pipeline": "trigger the build jobs",
    "deploy_build": "is the build passing",
    "deploy_scaleup": "provision additional machines",
    "deploy_scaledown": "decommission some machines",
}
