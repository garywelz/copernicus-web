"""The public channel's name, in one place. Everything that names the channel (the prompts, the series thumbnail mark, the transcript header) imports
CHANNEL_NAME from here. Decided by Gary on 2026-11-03 ("Frontiers of Science" collides with the existing podcast title "Copernicus AI: Frontiers of Research").
The documentation copy of the thumbnail generator (docs/design/series-thumbnail/make_thumbnail.py) cannot import this module and carries the same string;
tests/unit/test_channel_name.py fails if the two differ."""

CHANNEL_NAME = "CopernicusAI.fyi"
