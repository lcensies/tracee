import json
from collections import defaultdict
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()
load_dotenv(".local.env")


def has_subdirectory(directory, subdirectory_name):
    for entry in os.scandir(directory):
        if entry.is_dir() and entry.name == subdirectory_name:
            return True
    return False


reports_dir = os.environ["PERFTEST_REPORTS_DIR"]
if has_subdirectory(reports_dir, "tracee"):
    reports_dir = os.path.join(reports_dir, "tracee")

file_io_file = os.path.join(reports_dir, "file_io_metrics.json")


with open(file_io_file) as f:
    data = json.load(f)


# Aggregate counts by directory
def aggregate_counts(data):
    directory_counts = defaultdict(lambda: defaultdict(int))
    directory_processes = defaultdict(set)
    directory_entries = defaultdict(list)

    for entry in data:
        directory = str(Path(entry["pathname"]).parent)
        event_type = entry["event"]

        directory_counts[directory][event_type] += entry["count"]
        directory_processes[directory].add(entry["process"])
        directory_entries[directory].append(entry)

    return directory_counts, directory_entries, directory_processes


# Flatten the directory counts into a list of entries
def flatten_entries(directory_entries, directory_counts, directory_processes):
    flat_entries = []
    for directory, entries in directory_entries.items():
        process = (
            entries[0]["process"] if len(directory_processes[directory]) == 1 else "*"
        )
        if len(entries) == 1:
            entry = entries[0]
            entry["process"] = process
            entry.update(directory_counts[directory])  # Update entry with counts
            flat_entries.append(entry)
        else:
            aggregated_entry = {
                "pathname": f"{directory}/*",
                "process": process,
                "count": sum(directory_counts[directory].values()),
            }
            aggregated_entry.update(directory_counts[directory])
            flat_entries.append(aggregated_entry)
    return flat_entries


# Calculate the total count
total_count = sum(entry["count"] for entry in data)
threshold_count = 0.8 * total_count

# Recursive aggregation
current_entries = data
all_entries = []

while True:
    directory_counts, directory_entries, directory_processes = aggregate_counts(
        current_entries
    )
    flat_entries = flatten_entries(
        directory_entries, directory_counts, directory_processes
    )
    all_entries.extend(flat_entries)

    cumulative_count = sum(entry["count"] for entry in all_entries)
    if cumulative_count >= threshold_count:
        break

    # Prepare for next level of aggregation
    next_level_entries = []
    for directory, entries in directory_entries.items():
        if len(entries) > 1:
            for entry in entries:
                entry["pathname"] = str(Path(entry["pathname"]).parent)
            next_level_entries.extend(entries)
    current_entries = next_level_entries

# Sort and print top 5 entries by count
top_entries = sorted(all_entries, key=lambda x: x["count"], reverse=True)[:5]

print("Top 5 entries by count:")
for entry in top_entries:
    event_counts = ", ".join(
        f"{event}: {count}"
        for event, count in entry.items()
        if event not in ["pathname", "process", "count"]
    )
    print(
        f"{entry['pathname']} (Process: {entry['process']}): {entry['count']} ({event_counts})"
    )

output_path = os.path.join(os.environ["PERFTEST_REPORTS_DIR"], "top_io.json")
print(output_path)
with open(output_path, "w") as f:
    json.dump(top_entries, f, indent=2)
