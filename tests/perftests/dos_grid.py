# /usr/bin/env python
import os
import subprocess
import json
import numpy as np
from typing import Dict, List
import matplotlib.pyplot as plt
from pathlib import Path


def load_parameters_from_json(output_file):
    with open(output_file, "r") as file:
        data = json.load(file)
    return data


def call_dos(params, n_runs: int = 1) -> List[Dict]:
    dos_launcher = Path(__file__).parent.joinpath("dos_test.sh")

    results: List[Dict] = []

    for param_dict in params:
        print(f"Calling dos with params: {param_dict}")
        for i in range(n_runs):
            custom_env = os.environ.copy()
            custom_env = custom_env | param_dict

            print(f"DoS iterations: {i+1}/{n_runs}")

            output_file: str = f"dos_{i}.json"
            subprocess.run(
                [str(dos_launcher), "--output", output_file],
                check=True,
                env=custom_env,
            )

            results.append(load_parameters_from_json(output_file))

            os.remove(output_file)

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


DOS_N_RUNS = 3

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


def print_dependency(params, results, param_of_interest):
    for p, r in zip(params, results):
        print(p)
        print(r)
        print(
            f"{param_of_interest}: {p[param_of_interest]}, events: {r['totalEvents']}, lost/total: {r['lostTotalRatio']}"
        )


grid = GRID_PERF_BUF_SIZE
test_results = call_dos(grid, n_runs=DOS_N_RUNS)
means = get_means(test_results)

# print(f"Test results means: {means}")
# print_sleep_duration_to_events(grid_parameters, test_results)
print_dependency(grid, test_results, "TRACEE_PERF_BUFFER_SIZE")

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
