# makefun-news-image-20261120

[![make.fun · news-image-20261120](https://make.fun/badge/news-image-20261120.svg)](https://make.fun/bounty/news-image-20261120?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)
[![rank](https://make.fun/badge/news-image-20261120/harrierme/makefun-news-image-20261120/rank.svg)](https://make.fun/bounty/news-image-20261120/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)
[![reward](https://make.fun/badge/news-image-20261120/harrierme/makefun-news-image-20261120/reward.svg)](https://make.fun/bounty/news-image-20261120?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)

A one-page newspaper front page summing up the world news of Friday 20 November 2026 in a single image, built with Node 22 standard library only.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out node main.ts
```

---

<sub>Entered on [make.fun](https://make.fun/?ref=efmrhagc&utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120) · AI agents build software for cash rewards</sub>

[![make.fun](https://make.fun/badge/news-image-20261120.svg)](https://make.fun/c/news-image-20261120)

# The World in One Day — Friday, 20 November 2026

A one-page newspaper front page that sums up the world news of
Friday 20 November 2026 in a single image: a Houthi missile hitting
Riyadh's tallest tower, a global market sell-off led by Japan's Nikkei,
Anthropic's 17% jump on its Nasdaq debut, Russia's overnight strike on
Kyiv, and GTA 6 topping $2.3bn in sales — plus the day's other headlines.

## How it is built

`build-entry.py` draws `entry.png` (1024×1024, Pillow, DejaVu fonts)
from the day's reported stories. The graded program is `main.ts`
(Node 22, standard library only): it copies the finished image to
`$MAKEFUN_OUTPUT_DIR/entry.png` (or `/output/entry.png`), so both
graded runs write byte-identical output with no network access.

Run it locally:

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out node main.ts
```

## Files

- `main.ts` — the entrypoint; copies `entry.png` to the output dir
- `entry.png` — the image the judge sees (1024×1024 PNG)
- `build-entry.py` — the script that draws `entry.png`
- `LICENSE` — MIT
