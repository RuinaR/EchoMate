"""Bounded actual-message windows; source references never invent a turn."""

def reply_recipient(rows):
    """Resolve the latest actual bot reply, not an arbitrary sibling's peer."""
    latest=next((row for row in reversed(rows) if row.get('bot')),None)
    parent=next((row for row in rows if latest and row.get('id')==latest.get('reply') and row.get('id') is not None),None)
    return parent.get('speaker') if parent and not parent.get('bot') else None

def source_ids(rows,reply=None):
    """Protect the last bot/source pair and an actual requested reply pair."""
    by_id={row['id']:row for row in rows if row.get('id') is not None}
    latest=next((row for row in reversed(rows) if row.get('bot')),None)
    protected=set()
    for row in (latest,by_id.get(reply)):
        if row is None:continue
        if row.get('id') is not None:protected.add(row['id'])
        if row.get('reply') in by_id:protected.add(row['reply'])
    return protected


def evidence_window(rows,limit=6,reply=None):
    if limit<4:raise ValueError('Source window must fit two actual reply pairs')
    if len(rows)<=limit:return list(rows)
    protected=source_ids(rows,reply)
    indices={i for i,row in enumerate(rows) if row.get('id') in protected}
    for i in range(len(rows)-1,-1,-1):
        if len(indices)>=limit:break
        indices.add(i)
    return [row for i,row in enumerate(rows) if i in indices]


def trim_frame(frame,reply=None):
    """Drop one unprotected turn, or fail closed instead of losing provenance."""
    rows=frame['turns'];protected=source_ids(rows,reply)
    if len(rows)<=2:return False
    for i,row in enumerate(rows):
        if row.get('id') not in protected:
            rows.pop(i);return True
    return False
