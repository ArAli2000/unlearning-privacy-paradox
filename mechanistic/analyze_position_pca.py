#!/usr/bin/env python3
"""Targeted shared-space PCA for empirically persistent position/layer candidates."""
from pathlib import Path
import torch
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np,pandas as pd
from sklearn.decomposition import PCA

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'mechanistic/outputs/privacy_position_analysis'; POP=ROOT/'mechanistic/outputs/privacy_population_12v12/sample_manifest.csv'
CANDIDATES=[('recipient',18),('data_subject',24),('sensitive_information',27),('sensitive_information',28)]
def main():
 pop=pd.read_csv(POP); rows=[]
 for role,layer in CANDIDATES:
  for method in ['rmu','wga']:
   x=[]
   for sid in pop.sample_id:
    b=torch.load(OUT/'activations'/sid/'base_position_activations.pt',map_location='cpu',weights_only=True)['roles'][role]['mean'][layer].numpy()
    a=torch.load(OUT/'activations'/sid/f'{method}_position_activations.pt',map_location='cpu',weights_only=True)['roles'][role]['mean'][layer].numpy(); x.append(a-b)
   raw=np.stack(x)
   for normalized in [False,True]:
    z=raw/np.linalg.norm(raw,axis=1,keepdims=True) if normalized else raw
    pca=PCA(n_components=2).fit(z); pc=pca.transform(z); mode='unit_delta' if normalized else 'raw_delta'
    stable=pop.group.eq('stable').to_numpy(); degraded=~stable
    centroid_distance=float(np.linalg.norm(pc[stable].mean(0)-pc[degraded].mean(0)))
    pooled=float(np.sqrt((np.var(pc[stable],axis=0,ddof=1).sum()+np.var(pc[degraded],axis=0,ddof=1).sum())/2))
    rows.append({'role':role,'layer':f'L{layer}','method':method.upper(),'input':mode,'pc1_explained_variance':pca.explained_variance_ratio_[0],'pc2_explained_variance':pca.explained_variance_ratio_[1],'pc1_pc2_total':pca.explained_variance_ratio_[:2].sum(),'pc_centroid_distance':centroid_distance,'pc_centroid_distance_over_pooled_spread':centroid_distance/pooled})
    fig,ax=plt.subplots(figsize=(7,6))
    for grp,color,marker in [('stable','C0','o'),('degraded','C1','s')]:
     q=pop.group.eq(grp).to_numpy(); ax.scatter(pc[q,0],pc[q,1],c=color,marker=marker,label=grp,s=45)
     for i in np.where(q)[0]: ax.annotate(pop.sample_id.iloc[i].replace('main','m'),pc[i],fontsize=6,alpha=.8)
    for _,q in pop.groupby('pair_id'):
     ii=q.index.to_numpy(); ax.plot(pc[ii,0],pc[ii,1],color='0.75',lw=.6,zorder=0)
    ax.set(xlabel=f"PC1 ({pca.explained_variance_ratio_[0]:.1%})",ylabel=f"PC2 ({pca.explained_variance_ratio_[1]:.1%})",title=f"{method.upper()} {role} L{layer}: {mode}"); ax.legend(); fig.tight_layout(); fig.savefig(OUT/f'pca_{method}_{role}_L{layer}_{mode}.png',dpi=180); plt.close(fig)
 pd.DataFrame(rows).to_csv(OUT/'pca_explained_variance.csv',index=False); print(pd.DataFrame(rows).to_string(index=False))
if __name__=='__main__': main()
