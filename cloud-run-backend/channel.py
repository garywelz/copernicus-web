"""The public channel's name, in one place. Everything that names the channel imports it from here: CHANNEL_NAME for what is written (the series thumbnail mark, the transcript header),
CHANNEL_NAME_SPOKEN for what a script speaks (the show-name rules and the opening line of both generation modes). Decided by Gary on 2026-11-03 ("Frontiers of Science" collides with the existing podcast title "Copernicus AI: Frontiers of Research").
The documentation copy of the thumbnail generator (docs/design/series-thumbnail/make_thumbnail.py) cannot import this module and carries the same string;
tests/unit/test_channel_name.py fails if the two differ."""

CHANNEL_NAME = "CopernicusAI.fyi"                 # everything WRITTEN: the thumbnail mark, the transcript header, the descriptions
CHANNEL_NAME_SPOKEN = "CopernicusAI"             # everything a script SPEAKS: a voice model would read ".fyi" as "dot F Y I"
