"""
Run through all folds of Fridriksson
S2S model jointly optimized for both ASR and paraphasia detection
"""
import os
import shutil
import subprocess
import time
import datetime
import pandas as pd
from sklearn.metrics import f1_score, recall_score, precision_score
from collections import Counter
import pickle
from scipy import stats
import re
import socket
from tqdm import tqdm
import jiwer
import json
from helper_scripts.evaluation import *


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


TOT_EPOCHS = 120


def clean_FT_model_save(path):
    # keep only 1 checkpoint, remove optimizer
    save_dir = f"{path}/save"
    abs_directory = os.path.abspath(save_dir)

    files = os.listdir(abs_directory)

    # Filter files that start with 'CKPT'
    ckpt_files = [f for f in files if f.startswith("CKPT")]

    # If no CKPT files, return
    if not ckpt_files:
        print("No CKPT files found.")
        return

    # Sort files lexicographically, this works because the timestamp format is year to second
    ckpt_files.sort(reverse=True)

    # The first file in the list is the latest, assuming the naming convention is consistent
    latest_ckpt = ckpt_files[0]
    print(f"Retaining the latest CKPT file: {latest_ckpt}")

    # Remove all other CKPT files
    for ckpt in ckpt_files[1:]:
        shutil.rmtree(os.path.join(abs_directory, ckpt))
        print(f"Deleted CKPT file: {ckpt}")

    # remove optimizer
    optim_file = f"{abs_directory}/{latest_ckpt}/optimizer.ckpt"
    os.remove(optim_file)


def change_yaml(
    yaml_src,
    yaml_target,
    data_fold_dir,
    frid_fold,
    output_neurons,
    output_dir,
    base_model,
    freeze_arch_bool,
    loss_asr_weight,
):
    # copy src to tgt
    shutil.copyfile(yaml_src, yaml_target)

    # edit target file
    train_flag = False
    reset_LR = True  # if true, start lr with init_LR
    output_dir = f"{output_dir}/Fold-{frid_fold}"
    lr = 5.0e-4  # 1e-3 for frozen arch

    # copy original file over to new dir
    if not os.path.exists(output_dir):
        print("copying dir")
        shutil.copytree(base_model, output_dir, ignore_dangling_symlinks=True)
        clean_FT_model_save(output_dir)

    # replace with raw text
    with open(yaml_target) as fin:
        filedata = fin.read()
        filedata = filedata.replace("data_dir_PLACEHOLDER", f"{data_fold_dir}")
        filedata = filedata.replace("train_flag_PLACEHOLDER", f"{train_flag}")
        filedata = filedata.replace("FT_start_PLACEHOLDER", f"{reset_LR}")
        filedata = filedata.replace("epochs_PLACEHOLDER", f"{TOT_EPOCHS}")
        filedata = filedata.replace("frid_fold_PLACEHOLDER", f"{frid_fold}")
        filedata = filedata.replace("output_PLACEHOLDER", f"{output_dir}")
        filedata = filedata.replace(
            "output_neurons_PLACEHOLDER", f"{output_neurons}"
        )
        filedata = filedata.replace("lr_PLACEHOLDER", f"{lr}")
        filedata = filedata.replace(
            "freeze_ARCH_PLACEHOLDER", f"{freeze_arch_bool}"
        )
        filedata = filedata.replace(
            "loss_asr_weight_PLACEHOLDER", f"{loss_asr_weight}"
        )

        with open(yaml_target, "w") as fout:
            fout.write(filedata)

    return output_dir


if __name__ == "__main__":
    DATA_ROOT = (
        "/home/mkperez/speechbrain/AphasiaBank/data/Fridriksson_para_best_Word"
    )

    TRAIN_FLAG = True
    EVAL_FLAG = True
    OUTPUT_NEURONS = 500
    FREEZE_ARCH = False
    loss_asr_weight = 0.5  # between 0 and 1

    BASE_MODEL = f"<path>/<to>/<pretrained_model>"
    EXP_DIR = f"<new_path>/<to>/<finetuned_model>"

    if TRAIN_FLAG:
        yaml_src = "hparams/finetune_Scripts_base.yml"
        yaml_target = "hparams/finetune_Scripts_final.yml"
        start = time.time()

        i = 1
        count = 0
        while i <= 12:
            data_fold_dir = f"{DATA_ROOT}/Fold_{i}"

            change_yaml(
                yaml_src,
                yaml_target,
                data_fold_dir,
                i,
                OUTPUT_NEURONS,
                EXP_DIR,
                BASE_MODEL,
                FREEZE_ARCH,
                loss_asr_weight,
            )

            # # launch experiment
            # multi-gpu
            env = os.environ.copy()
            env["CUDA_VISIBLE_DEVICES"] = "0"
            port = find_free_port()  # Get a free port.
            print(f"free port: {port}")
            cmd = [
                "python",
                "-m",
                "torch.distributed.launch",
                f"--master_port={str(port)}",
                "train_multi-seq.py",
                f"{yaml_target}",
            ]

            p = subprocess.run(cmd, env=env)

            # p = subprocess.run(cmd)
            count += 1
            print(f"p.returncode: {p.returncode} | retry: {count}")
            # exit()

            if p.returncode == 0:
                i += 1

        end = time.time()
        elapsed = end - start
        print(f"Total Train runtime: {datetime.timedelta(seconds=elapsed)}")

    ##  Stat computation
    if EVAL_FLAG:
        para_eval(EXP_DIR, "mtl")
