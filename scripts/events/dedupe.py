"""Duplicate resolution across sources."""
from difflib import SequenceMatcher
from .model import PRECEDENCE, norm_title


def _rank(ev):
    """Lower is more authoritative. First-party beats aggregated."""
    return (PRECEDENCE.get(ev.get('sourceType'), 9), 0 if ev.get('firstParty') else 1)


def _same_slot(a, b):
    if a['startDate'] != b['startDate']:
        return False
    ta, tb = a.get('startTime'), b.get('startTime')
    if ta and tb and ta != tb:
        return False            # same day, clearly different sittings
    return True


def _same_place(a, b):
    ta, tb = (a.get('town') or '').lower(), (b.get('town') or '').lower()
    if ta and tb and ta != tb:
        return False
    return True


def is_duplicate(a, b, threshold=0.90):
    """Conservative. Same day, same town, and near-identical title.

    The threshold is deliberately high: merging two genuinely different events
    is a worse failure than showing two cards, because it silently hides
    something that is really happening.
    """
    if a.get('sourceEventId') and a.get('sourceEventId') == b.get('sourceEventId') \
            and a.get('sourceName') == b.get('sourceName'):
        return True
    if not _same_slot(a, b) or not _same_place(a, b):
        return False
    na, nb = norm_title(a['title']), norm_title(b['title'])
    if not na or not nb:
        return False
    if na == nb:
        return True
    if na in nb or nb in na:
        return True
    return SequenceMatcher(None, na, nb).ratio() >= threshold


def dedupe(events):
    """Collapse duplicates, keeping the most authoritative record.

    Returns (kept, removed_count). The surviving record keeps provenance for
    the sources it absorbed so we can explain where a listing came from.
    """
    kept = []
    removed = 0
    for ev in sorted(events, key=lambda e: (_rank(e), e['startDate'])):
        hit = None
        for k in kept:
            if is_duplicate(ev, k):
                hit = k
                break
        if hit is None:
            kept.append(ev)
            continue
        removed += 1
        alt = hit.setdefault('alsoReportedBy', [])
        entry = {'sourceName': ev['sourceName'], 'sourceUrl': ev['sourceUrl']}
        if entry not in alt and ev['sourceName'] != hit['sourceName']:
            alt.append(entry)
    return kept, removed
