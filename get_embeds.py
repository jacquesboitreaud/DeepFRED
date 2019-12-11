# -*- coding: utf-8 -*-
"""
Created on Tue Dec 10 15:42:38 2019

@author: jacqu

Embed non canonical edges with model, and visualize FR3D clusters. 
"""

import sys
import pickle
import torch
import torch.utils.data
from torch import nn, optim
import torch.nn.utils.clip_grad as clip
import torch.nn.functional as F

import pandas as pd 
import numpy as np

if (__name__ == "__main__"):
    sys.path.append("dataloading")
    from rgcn import Model, Loss
    from rnaDataset import rnaDataset, Loader
    from utils import *
    
    # Dict to get the edge embeddings 
    edges_d = {'label':[],'z1':[], 'z2':[]}
    
    load_model=True

    # config

    batch_size = 64
    load_path= 'saved_model_w/model1.pth'
    data_dir = '/home/mcb/users/jboitr/data/DF2'
    #data_dir = 'C:/Users/jacqu/Documents/GitHub/data/DeepFRED_data'
    
    cutoff=100
    
    #Load train set and test set
    loaders = Loader(path= data_dir,
                     N_graphs=cutoff, emb_size= 2, 
                     num_workers=0, batch_size=batch_size,EVAL=True)
    N_edge_types = loaders.num_edge_types
    _, _, test_loader = loaders.get_data()
    
    
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    feats_dim, h_size, out_size=2, 8, 4 # dims 
    model = Model(features_dim=feats_dim, h_dim=h_size, out_dim=out_size, 
                  num_rels=N_edge_types, num_bases=-1, num_hidden_layers=2).to(device)
    model.load_state_dict(torch.load(load_path))
    
    model.eval()
    t_loss=0
    with torch.no_grad():
        for batch_idx, (graph, edges, tmscores,labels) in enumerate(test_loader):
            print(labels)
            if(batch_idx%10==0):
                print(batch_idx)
            
            n= len(labels) # batch size
            tmscores=tmscores.to(device)
            graph=send_graph_to_device(graph,device)
            z_e1, z_e2 = model(graph, edges)
            
            # For loop over batch
            for i in range(n):
                # edge 1
                edges_d['label'].append(labels[i][0])
                edges_d['z1'].append(z_e1[i][0].item())
                edges_d['z2'].append(z_e1[i][1].item())
                # edge 2
                edges_d['label'].append(labels[i][1])
                edges_d['z1'].append(z_e2[i][0].item())
                edges_d['z2'].append(z_e2[i][1].item())
                
            df = pd.DataFrame.from_dict(edges_d)
            df.to_csv('edge_embeddings.csv')
