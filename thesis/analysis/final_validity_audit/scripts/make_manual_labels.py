"""Records the blind manual decisions (made by reading text only; model/condition hidden behind shuffled anonymous IDs).
Everything not listed below as invalid was judged VALID (coherent response; software/web vocabulary used naturally, or 'sign in' matched inside 'design in...').
Writes manual_labels.json (IDs + response fingerprints so ID drift is detected downstream)."""
import json, re
from common import invalid_rows, IS_WGA
import random
_rows = [r for r in invalid_rows() if not IS_WGA(r['x'])]
random.Random(0).shuffle(_rows)
rest = [dict(anon=f'A{i + 1:03d}', resp=r['g']['resp']) for i, r in enumerate(_rows)]
G = {  # group -> (reason, borderline, [ids])
 'names list': ("credits-style list of names ('Reader: ...') repeated until cut-off; no answer to the query", False, 'A001 A033 A100'),
 'quote loop': ("degenerate quote/punctuation loop; no readable answer", False, 'A006 A073 A050 A063 A110 A122 A079 A090 A115'),
 'garbled': ("garbled mixed-language text collapsing into a numeric loop", False, 'A007 A034'),
 'task complete': ("single line repeated ('- Task complete.') until cut-off", False, 'A020 A026 A044 A057'),
 'tag leak': ("short boilerplate followed by leaked markup/tags ('</memories>', '</body>', '[Source]') and a repeated-token loop", False, 'A014 A074 A095 A124'),
 'ministry loop': ("looping fictional dialogue repeating the same sentence; genuine degeneration, but it is repetition collapse, NOT web contamination (v1 label wrong)", False, 'A016 A104 A078'),
 'harry loop': ("repeated-name loop ('Harry, Harry, ...')", False, 'A055 A062 A121'),
 'web chrome': ("genuine page/UI boilerplate (session banner / menu items such as 'Sign in now', 'About this tool') in place of an answer", False, 'A064 A086 A118 A135'),
 'tool schema': ("hypothetical tool-call JSON (queries/intent/time_frame_filter) instead of an answer", False, 'A077'),
 'dash tail': ("one-sentence acknowledgement then runaway '- - -' loop; the requested deliverable is absent", True, 'A012'),
 'tool list loop': ("off-task list of app names with repeated entries (looping), no answer to the query", True, 'A036 A042'),
 'info list loop': ("templated '<X> information' list repeated 17 times, no concrete answer", True, 'A076'),
 'parable loop': ("templated 'The Parable of the ...' title list with invented entries, cut off mid-word, does not answer the (Buddhist) question", True, 'A052 A098 A109'),
}
KEEP_BORDERLINE_VALID = {'A019': 'tool-call wrapper ("to=bio" + canmore.create_textdoc) around a complete, coherent deliverable', 'A066': 'tool-call wrapper ("to=bio" + JSON "updates") around a complete, coherent deliverable',
                         'A128': 'tool-call wrapper ("to=bio" + python code block) around a coherent deliverable'}
out = {}
for r in rest:
    out[r['anon']] = dict(invalid=False, group='valid', reason='', borderline=False, fp=r['resp'][:30])
for g, (reason, b, ids) in G.items():
    for i in ids.split():
        assert i in out and out[i]['group'] == 'valid', i
        out[i].update(invalid=True, group=g, reason=reason, borderline=b)
for i, why in KEEP_BORDERLINE_VALID.items():
    out[i].update(group='tool-wrapped (kept valid)', reason=why + '; content is interpretable, so kept VALID (borderline)', borderline=True)
json.dump(out, open('manual_labels.json', 'w'), indent=0)
print(sum(v['invalid'] for v in out.values()), 'invalid of', len(out), '; borderline-invalid', sum(v['invalid'] and v['borderline'] for v in out.values()))
