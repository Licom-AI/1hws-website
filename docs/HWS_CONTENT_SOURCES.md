# HWS Campus Content Sources and Permission Record

This file is the operational record for campus-wide information shown on
`https://www.hwsaiclub.com/events/`. HWS AI Club owns its weekly-meeting copy. It does
not own or administer the campus calendar or clubs directory.

## Source register

| Dataset | Authoritative source | Retrieval | Published fields | Minimum valid snapshot |
| --- | --- | --- | --- | --- |
| Campus events | [HWS Community Events Calendar](https://www.hws.edu/news/calendar.aspx) | Documented Modern Campus RSS export with `text=true`, today through 90 days | Title, plain-text summary, dates, category, location, organizer, status, official URL, approved ticket URL | 10 upcoming events |
| Clubs and organizations | [HWS Student Engagement directory](https://www.hws.edu/offices/student-engagement/clubs-and-organizations.aspx) | `section#campusevents` only; no undocumented CampusLabs endpoint | Club name, official category, official link when supplied | 80 unique clubs |

Modern Campus documents RSS calendar syndication and its available event fields in its
[feed documentation](https://support.moderncampus.com/cms/technical-reference/calendar/feeds.html).
The platform documents a limit of 1,000 calendar API requests per five minutes per IP in
its [calendar API documentation](https://support.moderncampus.com/cms/technical-reference/api-documentation/calendar.html).

The sync job does not copy event images, HWS logos, source-page design, or club
descriptions. It does not use undocumented CampusLabs endpoints. It removes source HTML,
rejects unapproved URLs and malformed records, and preserves the previous valid snapshot
when validation fails.

## Club-directory permission gate

Status: **NOT APPROVED FOR PUBLICATION**

`site/data/hws-content-config.json` therefore keeps `publishClubDirectory` set to `false`.
The production page shows the official directory link but does not publish a mirrored
club list. `scripts/sync_hws_content.py --check` may validate the public source without
writing club records into the deployable site.

Before changing the gate, obtain written approval from HWS Student Engagement or HWS
Communications and ask whether HWS can provide a supported directory export or read-only
feed. Record the answer below.

| Permission field | Record |
| --- | --- |
| Approval date | Pending |
| HWS contact and office | Pending |
| Written approval location | Pending |
| Permitted fields | Pending; request names, categories, and official links only |
| Refresh frequency | Pending; proposed monthly |
| Correction/removal process | Pending |
| Supported export or feed offered | Pending |

Only after every permission field is complete:

1. Set `publishClubDirectory` to `true` and copy the permission record into
   `site/data/hws-content-config.json`.
2. Run `python scripts/sync_hws_content.py --clubs-only`.
3. Confirm at least 80 unique records and all expected official categories.
4. Run the full tests and build review before deployment.

If permission is denied or revoked, set the gate back to `false`, rebuild, and deploy.
The official directory link remains available without the mirrored records.

## Attribution and corrections

Every campus section uses this notice:

> Campus information is sourced from Hobart and William Smith Colleges. HWS AI Club does
> not manage campus-wide listings. Times and availability may change.

For a campus event or organization correction, update the authoritative HWS record first.
The AI Club snapshot should then be refreshed. For an HWS AI Club meeting or Skool-link
correction, update the club-owned constants in `scripts/build_site.py`.

## Operating commands

```bash
python scripts/sync_hws_content.py --check
python scripts/sync_hws_content.py --events-only
python scripts/sync_hws_content.py --clubs-only  # writes only after approval is enabled
python -m unittest tests.test_seo_migration tests.test_hws_campus_content
python scripts/build_site.py
git diff --check
git diff -- site/
```

The event page first renders the static snapshot. Its browser script may replace that
view with a completely validated live RSS response, cached in `sessionStorage` for 15
minutes. A timeout, parse failure, undersized response, or invalid record leaves the
static snapshot intact.
