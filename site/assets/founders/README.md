# Founder photos

Drop headshots here, named after the founder's slug in `scripts/build_site.py`:

| Founder | Expected file |
| --- | --- |
| Zackary Hanna | `zackary-hanna.jpg` |
| Dominic Schimizzi | `dominic-schimizzi.jpg` |

Then rebuild:

```bash
python3 scripts/build_site.py
```

## How it behaves

A founder shows a photo only if their `photo` key is set in `FOUNDERS` **and** the file
exists here. If the file is missing the build prints a warning and falls back to the
initials avatar, so the site never renders a broken image.

Only founders with a `photo` key are checked — Dominic has none set yet, so add one to his
entry in `scripts/build_site.py` if you want a photo for him too.

## Image guidance

- **Square**, at least 256×256. The CSS crops to a circle with `object-fit: cover` and
  `object-position: center top`, so a head-and-shoulders shot centred horizontally works best.
- Keep it small — these load on the homepage. Under ~100 KB is plenty at this display size
  (96 px on cards, 84 px on founder pages).
- JPEG for photos. If you use a different extension, update the `photo` path in `FOUNDERS`
  to match.

The photo is also emitted as `image` in each founder's schema.org `Person` markup, so it can
appear in search results.
