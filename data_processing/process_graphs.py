# -*- coding: utf-8 -*-
"""
Created on Sun Nov  3 17:11:42 2019

@author: jacqu

Reads off-the-shelf RNA graphs (structure using rna_classes.py)
Preprocesses : 
    removes dangling nodes 
    Checks graph not empty
    computes 3D node features (base angles)
    adds nucleotide identity as a node feature

Preprocess graphs 
  
"""

import numpy as np
import pickle 
import os 
import networkx as nx
import sys
import argparse


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.realpath(__file__))
    sys.path.append(os.path.join(script_dir, '..'))

    from data_processing.graph_utils import *
    from data_processing.angles import base_angles
    from data_processing.rna_classes import *
    from data_processing.utils import *
    
    parser = argparse.ArgumentParser()
    
    parser.add_argument('-i', '--graphs_dir', help="path to directory containing 'rna_classes' nx graphs ", 
                        type=str, default="C:/Users/jacqu/Documents/MegaSync Downloads/RNA_graphs")
    parser.add_argument('-c', "--cutoff", help="Max number of train samples. Set to -1 for all graphs in dir", 
                        type=int, default=200)
    
    parser.add_argument('-o', '--write_dir', help="path to directory to write preprocessed graphs ", 
                        type=str, default="../data/chunks")
    
    parser.add_argument('-d', "--debug", help="debug", 
                        type=bool, default=True)
    
     # =======

    args=parser.parse_args()
    
    # Hyperparams 
    gr_dir = args.graphs_dir
    annot_dir = args.write_dir
    
    angles = ['alpha', 'beta', 'gamma',  'delta', 'epsilon', 'zeta', 'chi', 'gly_base']
    nucleotides_id = {'A':0,
                      'U':1,
                      'G':2,
                      'C':3}
    
    print(f'Calculating {len(angles)} angles for each nt.')
    print(f'Graphs with node features will be saved to {annot_dir}')
    
    cpt, bads =0,0
    nucleotides_counter = 0 
    # Load list of graphs to ignore
    bad_graphs = set(pickle.load(open('bad_graphs.pickle','rb')))
    
    parse_dict = {}
        
    for pdb_id in os.listdir(gr_dir):
        
        if(cpt<args.cutoff):
            cpt+=1
            print(f'Reading {pdb_id}')
        
            if pdb_id in bad_graphs:
                #print('ignoring graph')
                continue
            
            # Dict for new node attributes 
            node_attrs = {}
            problem_nts = []
            
            node_attrs['angles']={} # dict to store angle values for each node
            node_attrs['identity']={} # dict to store nucleotide identity for each node 
        
            # Load graph  
            g = pickle.load(open(os.path.join(gr_dir,pdb_id), 'rb'))
            
            # 1/ Remove dangling nodes from graph 
            
            nodes =g.nodes(data=True)
            N = g.number_of_nodes()
            
            # Clean edges
            remove_self_edges(g) # Get rid of self edges (not sure its right?)
            g=nx.to_undirected(g)
            g= dangle_trim(g)
            N1 = g.number_of_nodes()
            
            # ================ Nucleotides parsing ===================
            for n, data in g.nodes(data=True):
                nucleotide = data['nucleotide']
                pdb_pos = int(nucleotide.pdb_pos)
                
                # Count context nodes
                nbr_neigh = len(g[n])
                
                if(nbr_neigh==0):
                    problem_nts.append(n)
                else:
                    
                    # Prev and next nucleotides 
                    prev_nt = find_nucleotide(g,n[0], pdb_pos-1)
                    next_nt = find_nucleotide(g,n[0], pdb_pos+1)
                    
                    # Nucleotide identity
                    n_type = nucleotide.nt
                    a = [0,0,0,0]
                    try:
                        a[nucleotides_id[n_type]]=1
                    except: # if weird nucleotide, a is set to all zeros
                        pass
                    node_attrs['identity'][n]=a
    
                    # Angles : 
                    angles = base_angles(nucleotide, prev_nt, next_nt)
                    nonzero = np.count_nonzero(angles)
                    if(nonzero<8): # Missing angles 
                        problem_nts.append(n) 
                        
                    # Store in node attributes dict 
                    node_attrs['angles'][n]=angles
            
            # ========= Create features and check all angles !=0 =============
        
            # Remove lonely nucleotides 
            G = g.copy()
            G.remove_nodes_from(problem_nts)
            
            # check all nodes have at least one neighbor:
            
            nbr_neigh = [len(G[n]) for n in G.nodes()]
            m = min(nbr_neigh)
            if(m==0): # Do not save this graph : one node is lonely . 
                print('Lonely node(s). passing')
                bads+=1
                continue
            
            N1 = G.number_of_nodes()
            if(N1<4): # Not enough nodes, do not process and do not save 
                print('less than 4 nodes. passing')
                bads+=1
                continue # empty graph, do not process and do not save 
                
            nucleotides_counter += N1
            
            # Add node feature to all nodes 
            assert(len(node_attrs['angles']) >= G.number_of_nodes())
            nx.set_node_attributes(G, node_attrs['angles'], 'angles')
            nx.set_node_attributes(G, node_attrs['identity'], 'identity')
            
            
            # Save
            with open(os.path.join(annot_dir,pdb_id),'wb') as f:
                pickle.dump(G, f)
                
    print(f'wrote {cpt} preprocessed graphs to {annot_dir}')
    print(f'removed {bads} too small graphs')
    print(f'Parsed {nucleotides_counter} clean nucleotides')  
            
            