# /usr/bin/env python

from shutil import rmtree
import os
import subprocess
import json
import numpy as np
from typing import Dict, List
# import matplotlib.pyplot as plt
from pathlib import Path
from time import sleep

# Note that TRACEE_PERF_BUFFER_SIZE defines size of generic
# events buffer while file writes and net events are stored
# in separate ones 


OUTPUT_DIR = "/tmp/dos_test"
DOS_N_RUNS = 1
# STABILIZIZATION_SLEEP_SECONDS = 120

# Define various grids based on which parameter do we want to verify
# grid_parameters = [{"TRACEE_MEM_CACHE_SIZE": "2048"}, {"TRACEE_MEM_CACHE_SIZE": "4096"}]
GRID_SLEEP = [
    # {"TRACEE_MEM_CACHE_SIZE": "4096", "DOS_SLEEP_DURATION_SEC": "0.0185"},
    {"TRACEE_MEM_CACHE_SIZE": "4096", "DOS_SLEEP_DURATION_SEC": "0.016"},
    # {"TRACEE_MEM_CACHE_SIZE": "4096", "DOS_SLEEP_DURATION_SEC": "0.025"},
    # {"TRACEE_MEM_CACHE_SIZE": "4096", "DOS_SLEEP_DURATION_SEC": "0.03"},
    # {"TRACEE_MEM_CACHE_SIZE": "4096", "DOS_SLEEP_DURATION_SEC": "0.04"},
]

DEFAULT_PARAMS = {"TRACEE_MEM_CACHE_SIZE": "4096", "DOS_SLEEP_DURATION_SEC": "0.016"}

GRID_DOS_CPU_LIMIT = [
        # {"DOS_CPU_LIMIT": "1"}
        {"DOS_CPU_LIMIT": "0.9"},
        {"DOS_CPU_LIMIT":  "0.8"},
        # {"DOS_CPU_LIMIT": "0.7"}
]

# GRID_PERF_BUF_SIZE = [
    # {"TRACEE_MEM_CACHE_SIZE": "2048", "TRACEE_PERF_BUFFER_SIZE": "1024"},
    # {"TRACEE_MEM_CACHE_SIZE": "2048", "TRACEE_PERF_BUFFER_SIZE": "4096"},
    # {"TRACEE_MEM_CACHE_SIZE": "4096", "TRACEE_PERF_BUFFER_SIZE": "8192", },
    # {"TRACEE_MEM_CACHE_SIZE": "4096", "TRACEE_PERF_BUFFER_SIZE": "16384",},
    # {"TRACEE_MEM_CACHE_SIZE": "4096", "TRACEE_PERF_BUFFER_SIZE": "32768", },
    # {"TRACEE_MEM_CACHE_SIZE": "4096", "TRACEE_PERF_BUFFER_SIZE": "65536", },
    # {"TRACEE_MEM_CACHE_SIZE": "2048", "TRACEE_PERF_BUFFER_SIZE": "16384"},
    # {"TRACEE_MEM_CACHE_SIZE": "2048", "TRACEE_PERF_BUFFER_SIZE": "65536"},
# ]

grid = [x | DEFAULT_PARAMS for x in GRID_SLEEP]



def load_json(input_file: str) -> Dict:
    with open(input_file, "r") as file:
        data = json.load(file)
    return data

def save_json(obj: Dict, output_file: str):
    with open(output_file, "w") as f:
        json.dump(obj, f)

def call_dos(params: List[dict], n_runs: int = 1) -> List[List[Dict]]:
    dos_launcher = Path(__file__).parent.joinpath("run_test_vm.sh")

    results: List[List[Dict]] = []
    run_idx: int = 0
    assert len(params) > 0
    for param_dict in params:
        local_res: List[Dict] = []
        print(f"Calling dos with params: {param_dict}")
        for i in range(n_runs):
            input_params_file: str = f"{OUTPUT_DIR}/input_{run_idx}.json"
            output_file: str = f"{OUTPUT_DIR}/dos_{run_idx}.json"

            custom_env = os.environ.copy()
            custom_env |= param_dict
            custom_env |= {"TRACEE_BENCHMARK_OUTPUT_FILE": output_file, "TRACEE_LOG_FILE": f"{OUTPUT_DIR}/tracee_{run_idx}.log"}

            print(f"DoS iterations: {i+1}/{n_runs}")
            subprocess.run(
                [str(dos_launcher)],
                check=True,
                env=custom_env,
            )

            local_res.append(load_json(output_file))
            save_json(param_dict, input_params_file)
            run_idx += 1
        
            # print(f"Sleeping {STABILIZIZATION_SLEEP_SECONDS} seconds to stabilize the environment")
            # sleep(STABILIZIZATION_SLEEP_SECONDS)

        results.append(local_res)


            # os.remove(output_file)

    return results


def get_means(test_results):
    metrics = test_results[0].keys()
    means = {
        metric: np.array([res[metric] for res in test_results]).mean()
        for metric in metrics
    }
    return means


Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

test_results = call_dos(grid, n_runs=DOS_N_RUNS)

# test_results = [
# [
# {"avgEbpfRate":4.376228627992081,"avgLostEventsRate":142056.875,"totalEvents":40432085,"lostEvents":40426892,"lostTotalRatio":0.9998715623990205},
# {'avgEbpfRate': 0, 'avgLostEventsRate': 102410.03730227992, 'totalEvents': 17635336, 'lostEvents': 17635144, 'lostTotalRatio': 0.9999891127676842},
# {'avgEbpfRate': 3.478817202151269, 'avgLostEventsRate': 153190.58674284074, 'totalEvents': 41278188, 'lostEvents': 41273289, 'lostTotalRatio': 0.9998813174648074},
# {'avgEbpfRate': 4.376228627992081, 'avgLostEventsRate': 142056.875, 'totalEvents': 40432085, 'lostEvents': 40426892, 'lostTotalRatio': 0.9998715623990205}
# ]
# ]


for inp, res in zip(grid, test_results):
    print(inp)
    print()
    for r in res:
        print(res)

    means = get_means(res)

    print(f"\nTest results means: {means}\n")
    print(f"\n{'-'*37}\n")


# rmtree(OUTPUT_DIR)
