# Autopilot story package

A **story package** is how researched, fully written stories enter Delaware
Beach Finds without a human typing them in. One file per research run:

```
automation/story-packages/story_package_YYYY-MM-DD.json
```

It is validated and staged by `scripts/ingest_story_package.py`. That script
never publishes. Eligible stories become `status: scheduled` with `approvedAt`
and an explicit `publishAt`. The hourly publisher (`scripts/publish_due.py`)
publishes them when they're due. Ineligible stories become `status: held` and
wait for a human.

Policy lives in `data/editorial-autopilot.json`. Cadence target: a new story
every **48 hours**. Hard maximum: **72 hours** between stories. Runway: at
least **15** scheduled stories and **30 days** of coverage.

## File shape

```json
{
  "packageId": "story_package_2026-10-02",
  "preparedAt": "2026-10-02T17:30",
  "preparedBy": "editorial-autopilot research run",
  "stories": [ { ...story... } ]
}
```

`packageId` must be unique per package. Re-ingesting the same package is a
no-op. A slug that already exists under a *different* package is rejected.

## Story fields

| Field | Required | Notes |
|---|---|---|
| `slug` | yes | lowercase-hyphenated, unique across `data/stories.json` |
| `headline`, `kicker`, `hook`, `lede` | yes | reader-facing copy |
| `body` | yes | the complete article as an HTML fragment (`<p>`, `<h2>`, `<ul>`), ending with a `Sources:` note. Not an outline. |
| `author` | yes | a desk id from `data/authors.json` |
| `category` | yes | a slug from `data/categories.json` |
| `placement` | yes | `cover`, `feature`, `secondary` or `standard`. The ingester makes the first scheduled story of each issue week its `cover` if that week has none. |
| `sources` | yes | list of `{"url", "publisher", "type", "supports"}`. `type` is `first-party`, `government`, `institutional` or `secondary`. `supports` says which claims this source backs. |
| `sourceNotes` | yes | how the sources were checked, and anything deliberately left out |
| `verifiedAt` | yes | `YYYY-MM-DD` the facts were checked |
| `heroImage` | yes | a file in `assets/images/scenes/` |
| `heroAlt` | yes | alt text. It must not name a place the image's record in `data/location-attributions.json` forbids. |
| `heroProvenance` | yes | why this image is honest for this story (place evidence, or "house illustration; no place claim") |
| `photoCredit` | no | defaults to "Delaware Beach Finds" |
| `seoTitle`, `seoDescription` | yes | |
| `places` | yes | town slugs used for "More from …" navigation |
| `riskClass` | yes | one key from `autoApprovableRiskClasses` or `heldRiskClasses` in the policy |
| `autoApprovalEligible` | yes | `true` only if every rule below holds |
| `heldReason` | if not eligible | why a human must look |
| `suggestedPublishAt` | if eligible | `YYYY-MM-DDTHH:MM` local. Use `python3 scripts/editorial_autopilot.py --prepare` for slots. |
| `relatedStories`, `readTime`, `metaTag`, `heroImageAlt` | no | |

## Auto-approval rules

`autoApprovalEligible: true` is accepted only if **all** of these hold.
Otherwise the whole package is rejected, so fix the story or mark it held:

* `riskClass` is auto-approvable: event field guide, nature explainer,
  seasonal observation, practical guide, history explainer, event preview or
  field note;
* at least 2 sources, at least 1 of them first-party, government or
  institutional, and the key premise does not rest on a single weak source;
* `verifiedAt` is no more than 7 days old;
* the body has at least 300 words;
* the prose contains no first-person visit claims, no "told DBF" or interview
  framing, and no attributed direct quotes. None of these may be invented, and
  autopilot never obtains real ones;
* `suggestedPublishAt` is in the future and at least 12 hours from any other
  scheduled or published story.

Anything in a held risk class goes in with `autoApprovalEligible: false` and
a `heldReason`. Held classes: allegations, legal, crime/investigative,
medical, political advocacy, interviews, first-person visits, product
endorsements, uncertain access/parking/fees/hours, community submissions,
sponsored, and single weak source.

## What a story may not contain

Every factual claim must be supportable by the listed sources. Never invent
quotes, visits, interviews, photos, observations, crowds, prices, access
conditions, event times or historical claims. Where sources disagree, the
story says so or leaves the claim out, and the ingester cannot catch that for
you. A photograph may only be presented as the place its provenance record
supports. When nothing fits, use a house illustration and say so in
`heroProvenance`.

## Commands

```
python3 scripts/editorial_autopilot.py --status          # runway report
python3 scripts/editorial_autopilot.py --prepare         # slots needed (JSON)
python3 scripts/ingest_story_package.py PACKAGE --dry-run
python3 scripts/ingest_story_package.py PACKAGE
python3 scripts/editorial_autopilot.py --check           # exit 1 on any SLA breach
python3 scripts/runway_guard.py                          # full failsafe check
```
