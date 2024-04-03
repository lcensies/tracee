# /usr/bin/env python

from shutil import rmtree
import os
import subprocess
import json
import numpy as np
from typing import Dict, List
import matplotlib.pyplot as plt
from pathlib import Path
from time import sleep

DOS_N_RUNS = 2
DOS_RUN_INTERVAL_SEC = 120

OUTPUT_DIR = "/tmp/tracee/dos_test"

# Define various grids based on which parameter do we want to verify
# grid_parameters = [{"TRACEE_MEM_CACHE_SIZE": "2048"}, {"TRACEE_MEM_CACHE_SIZE": "4096"}]
GRID_SLEEP = [
    {"TRACEE_MEM_CACHE_SIZE": "2048", "DOS_SLEEP_DURATION_SEC": "0.0185"},
    # {"TRACEE_MEM_CACHE_SIZE": "2048", "DOS_SLEEP_DURATION_SEC": "0.02"},
    # {"TRACEE_MEM_CACHE_SIZE": "2048", "DOS_SLEEP_DURATION_SEC": "0.023"},
]

GRID_PERF_BUF_SIZE = [
    # {"TRACEE_MEM_CACHE_SIZE": "2048", "TRACEE_PERF_BUFFER_SIZE": "1024"},
    # {"TRACEE_MEM_CACHE_SIZE": "2048", "TRACEE_PERF_BUFFER_SIZE": "4096"},
    {"TRACEE_MEM_CACHE_SIZE": "2048", "TRACEE_PERF_BUFFER_SIZE": "8192"},
    # {"TRACEE_MEM_CACHE_SIZE": "2048", "TRACEE_PERF_BUFFER_SIZE": "16384"},
    # {"TRACEE_MEM_CACHE_SIZE": "2048", "TRACEE_PERF_BUFFER_SIZE": "65536"},
]


def load_parameters_from_json(output_file):
    with open(output_file, "r") as file:
        data = json.load(file)
    return data


def call_dos(params: List[dict], n_runs: int = 1) -> List[Dict]:
    dos_launcher = Path(__file__).parent.joinpath("run_test_vm.sh")

    results: List[Dict] = []
    assert len(params) > 0
    param_dict = params[0]
    # for param_dict in params:
    print(f"Calling dos with params: {param_dict}")
    for i in range(n_runs):
        output_file: str = f"{OUTPUT_DIR}/dos_{i}.json"

        custom_env = os.environ.copy()
        custom_env |= param_dict
        custom_env |= {"TRACEE_BENCHMARK_OUTPUT_FILE": output_file}

        print(f"DoS iterations: {i+1}/{n_runs}")
        subprocess.run(
            [str(dos_launcher)],
            check=True,
            env=custom_env,
        )

        results.append(load_parameters_from_json(output_file))

        # os.remove(output_file)
        print(f"Sleeping for {DOS_RUN_INTERVAL_SEC} seconds to stabilize environment")
        sleep(DOS_RUN_INTERVAL_SEC)

    return results


def get_means(test_results):
    metrics = test_results[0].keys()
    means = {
        metric: np.array([res[metric] for res in test_results]).mean()
        for metric in metrics
    }
    # {
    #     "avgEbpfRate": 36.49090909090909,
    #     "avgLostEventsRate": 9029.580526060605,
    #     "totalEvents": 3002886,
    #     "lostEvents": 2987907,
    #     "lostTotalRatio": 0.995011798649699,
    # }
    return means


# def generate_and_display_plot(parameters, results):
#     plt.figure(figsize=(10, 6))
#     plt.plot(parameters, results, marker="o", linestyle="-", color="b")
#     plt.title("Dependency between Grid Parameter and Output")
#     plt.xlabel("Grid Parameter")
#     plt.ylabel("Output from JSON")
#     plt.grid(True)
#     plt.show()


def print_dependency(params, results, param_of_interest):
    for p, r in zip(params, results):
        print(p)
        print(r)
        print(
            f"{param_of_interest}: {p[param_of_interest]}, events: {r['totalEvents']}, lost/total: {r['lostTotalRatio']}"
        )


Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

grid = GRID_PERF_BUF_SIZE
# for x in grid:
#     print(f"grid: {grid}")
# exit(0)
test_results = call_dos(grid, n_runs=DOS_N_RUNS)

# exit(-1)

means = get_means(test_results)


# print(f"Test results means: {means}")
# print_sleep_duration_to_events(grid_parameters, test_results)
print_dependency(grid, test_results, "TRACEE_PERF_BUFFER_SIZE")


# rmtree(OUTPUT_DIR)

# print(means)

# Step 1: Call the Bash script

# Step 2: Load parameters from the output JSON
# data = load_parameters_from_json(output_file)
# # Assuming the JSON contains a list of parameters under a key, e.g., "parameters"
# parameters_from_json = data["parameters"]

# Step 3: Define a grid of other parameters and run the script with these parameters
# grid_parameters = np.linspace(1, 10, 10)  # For example, a grid from 1 to 10


#
# results = [run_script_with_parameters(param) for param in grid_parameters]

# Step 4 & 5: Generate and display the plot
# generate_and_display_plot(grid_parameters, results)
