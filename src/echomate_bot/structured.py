"""Internal JSON data decoding; never removes code fences from Discord output."""
import json
import re

def json_data(raw):
    if not isinstance(raw,str) or len(raw)>16000:raise ValueError('Invalid structured output')
    fenced=re.fullmatch(r'\s*```(?:json)?\s*\n?([\s\S]+?)\s*```\s*',raw)
    return json.loads(fenced.group(1) if fenced else raw)
