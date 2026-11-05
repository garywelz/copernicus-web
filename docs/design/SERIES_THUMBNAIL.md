# Series thumbnail: CopernicusAI.fyi

**Status:** DRAFT, for Gary's review. Direction C ("split field") chosen 2026-11-02. First use: episode 1 (`ever-math-260015`).

Every episode of the series carries the same thumbnail. **Only three things change from one episode to the next: the title, the subtitle and the motif.** Everything else below is fixed.

## Assets

| File | What it is |
|---|---|
| `docs/design/series-thumbnail/series-thumbnail-template-16x9.svg` | The template at 1280 × 720 (video thumbnail), shown with episode 1's title and motif. Text is outlines, so it renders the same anywhere. |
| `docs/design/series-thumbnail/series-thumbnail-template-square.svg` | The same at 3000 × 3000 (podcast artwork for Apple and Spotify). |
| `docs/design/series-thumbnail/make_thumbnail.py` | Writes both SVGs for a new episode from a title, a subtitle and a motif. PNGs are rendered from the SVGs. |

Run: `python make_thumbnail.py --font Inter.ttf --out DIR --slug EPISODE_ID --title "722" "papers" "overnight" --subtitle "OpenAI's mathematics release" --motif critical_strip` (needs `fontTools`). Render PNGs at the SVG's own size (1280 × 720, 3000 × 3000) with any SVG renderer; episode 1's were rendered with headless Chrome.

## Type

- **Font: Inter** (SIL Open Font License 1.1; https://github.com/google/fonts/tree/main/ofl/inter, the variable file). The font file is not stored in this repository; the generator turns text into outlines, so no font is needed to view the SVGs.
- **Title:** Inter ExtraBold (wght 800), tracking -1%. Line 1 (a number or one short word) at 176 px; later lines at 116 px. **A title of up to 5 words keeps this classic layout (at most 3 lines; a line that is too wide is shrunk to fit).** Colour: ink.
- **A longer title is never cut** (changed 2026-11-04; until then the code kept the first five words and dropped the rest, so "The Exponential Time Hypothesis is false?" was drawn "The Exponential Time Hypothesis is"). The code sets the whole title in 2 to 4 lines of one size, choosing the fewest lines whose font is within 10% of the largest that fits, shrunk to fit the panel and the space above the subtitle. If a line (a very long word, or a long title) would need a font smaller than 64 px (the 3000-px square scales this), the thumbnail step **fails with a plain message** ("… is too long to set legibly on the series template without cutting words. Give a shorter thumbnail_title") and writes no thumbnail: the episode still generates, with the default series artwork, and the job record and the route answer carry the message (`thumbnail_error_message`, `thumbnail_warning`). The same rule applies to the subtitle (smallest 16 px).
- **Choosing the words:** a curated generate or check-script request may carry `thumbnail_title` and `thumbnail_subtitle` (both optional). When given, they are drawn instead of the episode title: the title whole (a colon in it stays), the subtitle as given (none if only a title is given). When not given, the episode title is used and split at its first colon, as before.
- **Subtitle:** Inter Medium (wght 500), 32 px, ink at 80% opacity. One short line, sentence case, no full stop.
- **Series mark:** Inter Medium, 25 px, tracking +10%, ink. Always the exact text `CopernicusAI.fyi` (the channel name; `cloud-run-backend/channel.py`), always top-left. (Until 2026-11-03 the mark read `CopernicusAI · Frontiers of Science`; the name was dropped because it collides with the existing podcast title "Copernicus AI: Frontiers of Research".)

## Colours (three, no more)

| Role | Value |
|---|---|
| Ink (text, dark panel) | `#1B2A41` |
| White (title panel) | `#FFFFFF` |
| Gold (the one accent: dots and the inner band's outline) | `#D9A441` |

Two supporting tints are derived from ink, not new colours: `#E8ECF2` for lines on the dark panel and `#2B3C58` for the inner band's fill. Contrast: ink on white about 14:1.

## Grid and safe areas (1280 × 720)

- **Margin:** 70 px left and top.
- **Title panel:** x 0 to 800, white. **Motif panel:** x 800 to 1280, ink.
- **Series-mark slot:** baseline y 76, x 70.
- **Title slot:** x 66 to 760; baselines y 300, 440, 560.
- **Subtitle slot:** baseline y 630, x 72.
- **Motif slot:** x 900 to 1180, y 60 to 600, centred in the dark panel.
- **Keep clear: the bottom-right 220 × 90 px (x 1060 to 1280, y 630 to 720).** Video players print a timestamp there. Nothing is drawn in it except the panel colour.
- Everything that matters sits inside the middle 90% of each edge, so a crop to a phone feed loses nothing.

## Square artwork (3000 × 3000)

The split turns horizontal: title panel on top (y 0 to 1830), motif panel below (y 1830 to 3000), with the motif laid on its side. This reads better at the small sizes podcast apps use than a left-right split, because the title keeps the full width. Margin 200 px; series mark at the top; title at up to 430 px, the number and the first word on one line; subtitle at baseline y 1720; motif in x 300 to 2700, y 1990 to 2770.

## Motifs

The motif is **drawn line geometry**, always in the same style: round-capped lines (5 px at 1280 wide), a dashed centre line (3 px), gold-outlined bands, gold dots with an ink ring. No equations, symbols, text, logos, photographs, people or arrows. Each episode gets a motif from its subject (a graph, a curve, a lattice), in the same line weights and the same two panel colours.

**Episode 1: `critical_strip`.** The critical strip of the Riemann zeta function: two outer vertical lines, a dashed critical line down the middle, a narrower inner band outlined in gold, and eight gold dots (zeros) confined inside the inner band. Drawn as geometry only. Add a new motif by adding a function to `MOTIFS` in `make_thumbnail.py` that fills the same slot.

## Rules

- Calm and credible; the channel is honesty-first. Never use the words "proven", "verified" or "breakthrough"; no clickbait styling, shocked faces, arrows or marks of any company.
- Never an AI-generated or real face, and never a photograph.
- The title states the subject, not a result.

## Where the files go (private episodes)

For an unpublished episode, the PNGs are stored in the private media bucket like its other media: `thumbnails/<episode_id>-thumb.png` (1280 × 720) and `episode-images/<episode_id>-artwork-3000.png` (3000 × 3000), with the record's `thumbnail_url` and `artwork_url` holding the public form of the address, which answers 404 until the episode is published. Replaced files are kept under `thumbnails/previous/`, which publishing does not copy.
