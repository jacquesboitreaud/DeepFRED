# -*- coding: utf-8 -*-
"""
Created on Sat Oct 26 18:06:44 2019

@author: jacqu

Dataset class for pairs of nodes and RNA graphs handling

TODO: Collate block, loader + change paths to files 
"""

import os 
import sys
if __name__ == "__main__":
    sys.path.append("..")
    
import torch
import dgl
import pandas as pd
import pickle
import numpy as np
import random
import itertools
from collections import Counter

from rna_classes import *
import networkx as nx


from tqdm import tqdm
from rna_classes import *

from torch.utils.data import Dataset, DataLoader, Subset


def collate_block(samples):
    # Collates samples into a batch
    # The input `samples` is a list of pairs
    #  (graph, label).
    graphs, edges, targets = map(list, zip(*samples))
    batched_graph = dgl.batch(graphs)
    edges_i = [(e1[0][1],e1[1][1],e2[0][1],e2[1][1]) for (e1,e2) in edges]
    
    return batched_graph, edges_i, targets


class rnaDataset(Dataset):
    """ 
    pytorch Dataset for training on pairs of nodes of RNA graphs 
    """
    def __init__(self, rna_graphs_path,
                 N_graphs,
                 emb_size=1,
                debug=False):
        
        self.path = rna_graphs_path
        self.all_graphs = os.listdir(self.path)[:N_graphs] # Cutoff number 
        self.n = len(self.all_graphs)
        self.emb_size = emb_size
        # Build edge map
        self.edge_map, self.edge_freqs = self._get_edge_data(simplified=True)
        
        # Number of edge categories (4 if simplified)
        self.num_edge_types = len(self.edge_map)
        print(f"found {self.num_edge_types} edge types, frequencies: {self.edge_freqs}")
        
        if(debug):
            # special case for debugging
            pass
            
    def __len__(self):
        return self.n
    
    def __getitem__(self, idx):
        # gets the RNA graph n°idx in the list
        with open(os.path.join(self.path, self.all_graphs[idx]),'rb') as f:
            graph = pickle.load(f)
            e1,e2, tmscore = pickle.load(f)
            
        e1_vertices=(e1[0][1], e1[1][1])
        e2_vertices=(e2[0][1], e2[1][1])
        print(e1_vertices, e2_vertices)
        e1 = [n[1] for n in graph.nodes()]
        print(e1)
        
        graph = nx.to_undirected(graph)
        one_hot = {edge: torch.tensor(self.edge_map[label]) for edge, label in
                   (nx.get_edge_attributes(graph, 'label')).items()}

        nx.set_edge_attributes(graph, name='one_hot', values=one_hot)
        
        # Create dgl graph
        g_dgl = dgl.DGLGraph()
        g_dgl.from_networkx(nx_graph=graph, edge_attrs=['one_hot'])
        
        g_dgl.ndata['h'] = torch.ones((g_dgl.number_of_nodes(), self.emb_size)) # nodes embeddings 
        
        return g_dgl,(e1,e2), tmscore
    
    def _get_edge_data(self,simplified=True):
        """
        Get edge type statistics, and edge map.
        """
        edge_counts = Counter()
        print("Collecting edge data...")
        graphlist = os.listdir(self.path)
        for g in tqdm(graphlist):
            graph = pickle.load(open(os.path.join(self.path, g), 'rb'))
            edges = {e_dict['label'] for _,_,e_dict in graph.edges(data=True)}
            edge_counts.update(edges)
        
        if(simplified): # Only three classes
            # Edge map with Backbone (0), WW (1), stackings (2) and others (3)
            edge_map={'B35':0,
                      'B53':0,
                      'CWW':1,
                      'S33':2,
                      'S35':2,
                      'S53':2,
                      'S55':2}
            for label in edge_counts.keys():
                if label not in edge_map:
                    edge_map[label]=3
        else:
            # Edge map with all different types of edges (FR3D edges)
            edge_map = {label:i for i,label in enumerate(sorted(edge_counts))}
        
        
        IDF = {k: np.log(len(graphlist)/ edge_counts[k] + 1) for k in edge_counts}
        return edge_map, IDF
        
    
class Loader():
    def __init__(self,
                 path='/home/mcb/users/jboitr/data/DeepFRED_data',
                 N_graphs=10,
                 emb_size=1,
                 batch_size=64,
                 num_workers=4,
                 debug=False):
        """
        Wrapper for test loader, train loader 
        Uncomment to add validation loader 

        """

        self.batch_size = batch_size
        self.num_workers = num_workers
        self.dataset = rnaDataset(rna_graphs_path=path,
                                  N_graphs= N_graphs,
                                  emb_size=emb_size,
                                  debug=debug)
        self.num_edge_types = self.dataset.num_edge_types

    def get_data(self):
        n = len(self.dataset)
        print(f"Splitting dataset with {n} samples")
        indices = list(range(n))
        # np.random.shuffle(indices)
        np.random.seed(0)
        split_train, split_valid = 0.8, 0.8
        train_index, valid_index = int(split_train * n), int(split_valid * n)
        
        train_indices = indices[:train_index]
        valid_indices = indices[train_index:valid_index]
        test_indices = indices[valid_index:]
        
        train_set = Subset(self.dataset, train_indices)
        valid_set = Subset(self.dataset, valid_indices)
        test_set = Subset(self.dataset, test_indices)
        print(f"Train set contains {len(train_set)} samples")


        train_loader = DataLoader(dataset=train_set, shuffle=True, batch_size=self.batch_size,
                                  num_workers=self.num_workers, collate_fn=collate_block)

        # valid_loader = DataLoader(dataset=valid_set, shuffle=True, batch_size=self.batch_size,
        #                           num_workers=self.num_workers, collate_fn=collate_block)
        
        test_loader = DataLoader(dataset=test_set, shuffle=True, batch_size=self.batch_size,
                                 num_workers=self.num_workers, collate_fn=collate_block)


        # return train_loader, valid_loader, test_loader
        return train_loader, 0, test_loader