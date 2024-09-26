#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 24 12:16:06 2024

@author: mtrubshaw
"""

"""Fit a GLM and perform statistical significance testing.

"""

import numpy as np
import os
import pandas as pd
from scipy import stats
import mne
import glmtools as glm
from osl_dynamics.analysis import power

bl_window = [0,6]
freq_n = 'betas'

os.makedirs('plots', exist_ok=True)
os.makedirs('data', exist_ok=True)
os.makedirs('plots/compiled_plots', exist_ok=True)
# Load target data


beta_ = np.load(f'data/psd_tf_{freq_n}_range_meg.npy')
time = np.arange(beta_.shape[-1])/250
beta_ = mne.baseline.rescale(beta_,time,bl_window)
data = np.mean(beta_[:,[4,30]],axis=1)


# Load regressor data
demographics = pd.read_csv("../demographics/task_demographics.csv")
grip_r = demographics["Grip_strength_r"].values
grip_l = demographics["Grip_strength_l"].values
grip = np.mean(np.vstack((grip_r,grip_l)),axis=0)



category_list = demographics["Group"].values
category_list[category_list == "HC"] = 1
category_list[category_list == "ALS"] = 2
category_list[category_list == "rALS"] = 2
category_list[category_list == "PLS"] = 3
category_list[category_list == "rPLS"] = 3
category_list[category_list == "FDR"] = 3
category_list[category_list == "rFDR"] = 3
uniques = np.unique(category_list)

age = demographics["Age"].values

gender = []
for g in demographics["Sex"].values:
    if g == "M":
        gender.append(0)
    else:
        gender.append(1)
gender = np.array(gender)


missing_struc = demographics["Missing_struc"].values


# Create GLM dataset
data = glm.data.TrialGLMData(
    data=data,
    category_list=category_list,
    age=age,
    gender=gender,
    dim_labels=["Subjects", "Frequencies", "Parcels"],
    missing_struc=missing_struc,
    grip=grip,
)

# Design matrix
DC = glm.design.DesignConfig()
DC.add_regressor(name="HC", rtype="Categorical", codes=1)
DC.add_regressor(name="ALS", rtype="Categorical", codes=2)
# DC.add_regressor(name="FDR", rtype="Categorical", codes=3)
DC.add_regressor(name="Sex", rtype="Parametric", datainfo="gender", preproc="z")
DC.add_regressor(name="Age", rtype="Parametric", datainfo="age", preproc="z")
DC.add_regressor(name="Missing Structural", rtype="Parametric", datainfo="missing_struc", preproc="z")
# DC.add_regressor(name="Grip", rtype="Parametric", datainfo="grip", preproc="z")


DC.add_contrast(name="ALS-HC", values=[1, -1, 0, 0, 0])
# DC.add_contrast(name="grip", values=[0, 0, 0, 0, 0,1])
# DC.add_contrast(name="FDR-HC", values=[-1, 0, 1, 0, 0, 0])
# DC.add_contrast(name="ALS-FDR", values=[0, 1, -1, 0, 0, 0])


design = DC.design_from_datainfo(data.info)
design.plot_summary(savepath="plots/glm_design.png", show=False)
design.plot_leverage(savepath="plots/glm_leverage.png", show=False)
design.plot_efficiency(savepath="plots/glm_efficiency.png", show=False)

# Fit the GLM
model = glm.fit.OLSModel(design, data)

def do_stats(contrast_idx, metric="tstats"):
    # Max-stat permutations
    perm = glm.permutations.MaxStatPermutation(
        design=design,
        data=data,
        contrast_idx=contrast_idx,
        nperms=1000,
        metric=metric,
        tail=0,  # two-tailed t-test
        pooled_dims=(1),  # pool over channels
        nprocesses=16,
    )
    null_dist = perm.nulls

    # Calculate p-values
    if metric == "tstats":
        tstats = abs(model.tstats[contrast_idx])
        percentiles = stats.percentileofscore(null_dist, tstats)
    elif metric == "copes":
        copes = abs(model.copes[contrast_idx])
        percentiles = stats.percentileofscore(null_dist, copes)
    pvalues = 1 - percentiles / 100

    return pvalues

for i in range(model.copes.shape[0]):
    cope = model.copes[i]
    pvalues = do_stats(contrast_idx=i)
    print(cope)
    print(pvalues)
    mask = pvalues<0.05
    np.save(f"data/contrast_{i}.npy", cope)
    np.save(f"data/contrast_{i}_pvalues.npy", pvalues)

for unique in uniques:
    count = np.count_nonzero(category_list==unique)
    print('Group',unique,' - ',count)
np.save('data/beta_bl_pval_mask.npy',mask)