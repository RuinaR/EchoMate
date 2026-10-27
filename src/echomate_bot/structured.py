"""Internal JSON data decoding; never removes code fences from Discord output."""
import json
import re


def source_spans(text,quote):
    """Exact code-point anchors, including overlapping occurrences; no NLP."""
    if not isinstance(text,str) or not isinstance(quote,str) or not quote:
        raise ValueError('Nonempty source quote required')
    found=[];start=text.find(quote)
    while start>=0:
        found.append((start,start+len(quote)));start=text.find(quote,start+1)
    return tuple(found)


def source_span(text,quote,span=None):
    """Validate an explicit offset, or require one unambiguous occurrence."""
    if span is None:
        spans=source_spans(text,quote)
        if len(spans)!=1:raise ValueError('Unique exact source anchor required')
        return spans[0]
    if (not isinstance(text,str) or not isinstance(quote,str) or not quote or
        not isinstance(span,(list,tuple)) or len(span)!=2 or
        any(type(i) is not int for i in span) or not 0<=span[0]<span[1]<=len(text) or
        text[span[0]:span[1]]!=quote):raise ValueError('Exact source span required')
    return tuple(span)

def json_data(raw):
    if not isinstance(raw,str) or len(raw)>16000:raise ValueError('Invalid structured output')
    fenced=re.fullmatch(r'\s*```(?:json)?\s*\n?([\s\S]+?)\s*```\s*',raw)
    return json.loads(fenced.group(1) if fenced else raw)
