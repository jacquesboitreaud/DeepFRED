# -*- coding: utf-8 -*-
"""
Created on Fri Mar 13 18:04:24 2020

@author: jacqu
"""

import pickle
import os

gr_dir = '../data/chunks'

graphs = os.listdir(gr_dir)

cpt=0 
graphs_cpt = 0
d = {'chi':[],
     'psi':[],
     'delta':[]}

for gid in graphs:
    graphs_cpt+=1
    if(graphs_cpt%100==0):
        print(graphs_cpt)

    with open(os.path.join(gr_dir,gid),'rb') as f:
        g = pickle.load(f)
        nn = g.number_of_nodes()
        
    for n, data in g.nodes(data=True):
        # Get angles 
        d['chi'].append(data['chi'])
        d['psi'].append(data['gly_base'])
        d['delta'].append(data['delta'])
    
with open('angles_distrib.pickle', 'wb') as f:
    pickle.dump(d,f)