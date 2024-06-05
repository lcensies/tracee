from os import environ
import os
import re
import subprocess
from pathlib import Path
from dotenv import load_dotenv
import shutil

load_dotenv()

load_dotenv(".local.env")


def get_next_experiment_num():
    directory = environ["EXPERIMENTS_DIR"]
    # Initialize the largest number to a very small value
    largest_number = -1

    # Regular expression pattern to match subdirectory names starting with a number and a hyphen
    pattern = re.compile(r"^(\d+)-")

    # Iterate over the items in the directory
    for item in os.listdir(directory):
        # Construct the full path of the item
        item_path = os.path.join(directory, item)
        # Check if the item is a directory and its name matches the pattern
        if os.path.isdir(item_path):
            match = pattern.match(item)
            if match:
                # Extract the number from the matched pattern
                number = int(match.group(1))
                # Update the largest number found so far
                if number > largest_number:
                    largest_number = number

    # Return the next number
    return largest_number + 1


def save_dotenv(data, output_dir):
    with open(os.path.join(output_dir, ".env"), "w") as dotenv_file:
        for key, value in data.items():
            dotenv_file.write(f"{key}={value}\n")


def call_test(params: dict, label: str = "run"):
    launcher = Path(__file__).parent.joinpath("run_test_vm.sh")

    # custom_env = os.environ.copy() | params
    output_subdir_name = f"{get_next_experiment_num()}-{label}"
    output_dir = f"{environ['EXPERIMENTS_DIR']}/{output_subdir_name}/"
    os.mkdir(output_dir)

    export_env = {"USER": os.environ["USER"]}
    subprocess.run(
        str(launcher),
        check=True,
        env=params | export_env,
    )


for i in [0.05, 0.1, 0.15, 0.2, 0.5]:
    call_test(
        {"TRACEE_CPU_LIMIT": str(i)},
        f"base-cpu-lim-{i}",
    )
