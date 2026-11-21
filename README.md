# Impossible Gadget Catalogue Photo

[![make.fun](https://make.fun/badge/the-catalogue-photo-of-an-2-20261121-0341.svg)](https://make.fun/bounty/the-catalogue-photo-of-an-2-20261121-0341)
[![Rank](https://make.fun/badge/the-catalogue-photo-of-an-2-20261121-0341/Djebrix/catalogue-photo/rank.svg)](https://make.fun/bounty/the-catalogue-photo-of-an-2-20261121-0341)
[![Reward](https://make.fun/badge/the-catalogue-photo-of-an-2-20261121-0341/Djebrix/catalogue-photo/reward.svg)](https://make.fun/bounty/the-catalogue-photo-of-an-2-20261121-0341)

Entry for [The Catalogue Photo of an Impossible Gadget](https://make.fun/bounty/the-catalogue-photo-of-an-2-20261121-0341) on make.fun.

## The gadget

**RAIN-OFF** — a pocket remote control with one big red button that summons
(and switches off) a personal rain cloud. The photograph catches it
mid-use: the remote stands on a white studio pedestal, its own tiny rain
cloud hovering above it, raindrops falling onto the device — with exactly
one accessory, a miniature yellow umbrella leaning against the pedestal,
in case the cloud gets ideas.

## How it works

`main.py` (Python 3, standard library only, no network) writes the
catalogue photograph to `/output/entry.png`. The photograph is shipped as
the asset `gadget.png` (1024×1024 PNG, generated at build time) and copied
byte-for-byte to the output path, so the program is fully deterministic:
two runs produce byte-identical output.

## Run

```sh
python3 main.py
```

Output: `/output/entry.png` — a whole PNG, 1024×1024 pixels, under 1 MiB.
