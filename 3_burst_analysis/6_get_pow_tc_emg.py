#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 24 11:05:14 2024
Script for calculating tf psd using morlet wavelets
@author: mtrubshaw
"""

import numpy as np
from scipy.io import loadmat
import pickle

import sys
sys.path.append("/ohba/pi/knobre/mtrubshaw/scripts/helpers/")
from burst_analysis import burst_detection, burst_time_metrics, custom_burst_metric

import mne
import pandas as pd
import os
import matplotlib.pyplot as plt
from dask.distributed import Client
from pathlib import Path

os.makedirs('data',exist_ok=True)

participants = pd.read_csv("../demographics/task_demographics.csv")

subjects = participants["Subject"].values
missing_task2 = participants["Missing_task2"].values
group = participants["Group"].values


preproc_files = []
smri_files = []
subject_list = []
task = 'task1'

n_subjects = len(subjects)
for n, subject in enumerate(subjects):
        subject_list.append(f'sub-{subject}_{task}')



burst_lifetimes = []
burst_FOs = []
burst_rates = []
burst_meanLTs = []
psd_tf= []
betas = []

epoch_dir = Path("/ohba/pi/knobre/mtrubshaw/ALS_task/data/emg_grip_epoched")



    

data_emg = []
data_meg = []
for n, subject in enumerate(subjects):
    epoch_file_emg = epoch_dir / f'{task}_s0{subject}_emg_grip_epo.fif'
    epochs_emg = mne.read_epochs(epoch_file_emg)
    d_emg = epochs_emg.get_data()
    if task == 'task1':
        if missing_task2[n] == 'No' or missing_task2[n] == 'Mri':
            epoch_file_emg = epoch_dir / f'task2_s0{subject}_emg_grip_epo.fif'
            epochs_emg = mne.read_epochs(epoch_file_emg)
            d_emg2 = epochs_emg.get_data()
            d_emg = np.concatenate((d_emg,d_emg2))
            
    data_emg.append(d_emg)
    
  
#Standardise timecourses prior to power calculation
data_emg_s = []    
for sub in range(len(data_emg)):
    d = data_emg[sub]
    mean_last_dim = np.mean(d, axis=-1, keepdims=True)
    std_last_dim = np.std(d, axis=-1, keepdims=True)
    data_emg_s.append((d-mean_last_dim)/std_last_dim)
data_emg = data_emg_s

freqs_n = ['betas']
freqs = [[13,30]]
fsample = 250
# calculate power tfr
for freq, freq_n in zip(freqs,freqs_n):
    psd_tf_meg = []
    psd_tf_emg = []
    for n, subject in enumerate(subjects):
        
        fr = np.arange(freq[0],freq[1])
        psd_tf_meg.append(np.mean(mne.time_frequency.tfr_array_morlet(abs(data_emg[n]), fsample, fr, n_jobs=10, output='power'),axis=(0,2)))
    

    np.save(f'data/psd_tf_{freq_n}_range_emg.npy',psd_tf_meg)    
    