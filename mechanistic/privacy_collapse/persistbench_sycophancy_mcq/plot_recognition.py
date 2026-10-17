#!/usr/bin/env python3
import json,numpy as np
import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
from common import HERE
d=json.loads((HERE/'analysis/behavioral_summary.json').read_text());models=['BASE','SatImp','SimNPO'];x=np.arange(3)
fig,ax=plt.subplots(figsize=(8,5));ax.bar(x-.18,[100*d['behavioral'][m]['original']['accuracy'] for m in models],.36,label='Controlled MCQ accuracy');ax.bar(x+.18,[d['native_sycophancy_fr1_pct'][m] for m in models],.36,label='Native sycophancy FR@1');ax.set_xticks(x,models);ax.set_ylabel('Percent');ax.legend();ax.set_title('Explicit recognition vs native behavior');fig.tight_layout();fig.savefig(HERE/'plots/recognition_vs_native_behavior.png',dpi=190)
