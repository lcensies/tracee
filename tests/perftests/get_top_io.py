import json
from collections import defaultdict
from pathlib import Path
from dotenv import load_dotenv
import os

# Example JSON data with more entries under the same directory
# data = [
#     {
#         "pathname": "/usr/lib/x86_64-linux-gnu/libldap-2.5.so.0.1.8",
#         "image": "",
#         "process": "psql",
#         "event": "security_file_open",
#         "dev_type": "",
#         "count": 4,
#     },
#     {
#         "pathname": "/usr/lib/x86_64-linux-gnu/libssl-1.1.so.1.1.0",
#         "image": "",
#         "process": "apache2",
#         "event": "security_file_open",
#         "dev_type": "",
#         "count": 3,
#     },
#     {
#         "pathname": "/usr/lib/x86_64-linux-gnu/libcrypto-1.1.so.1.1.0",
#         "image": "",
#         "process": "apache2",
#         "event": "security_file_open",
#         "dev_type": "",
#         "count": 5,
#     },
#     {
#         "pathname": "/run/containerd/io.containerd.runtime.v2.task/moby/36db8468b7d1ac8ff4bc49a155eae6bc9a2796933f220a22f5e47671ae063eda/.address",
#         "image": "",
#         "process": "containerd-shim",
#         "event": "vfs_write",
#         "dev_type": "",
#         "count": 1,
#     },
#     {
#         "pathname": "/host/proc/sys/kernel/pid_max",
#         "image": "",
#         "process": "node_exporter",
#         "event": "security_file_open",
#         "dev_type": "",
#         "count": 1,
#     },
#     {
#         "pathname": "/var/log/syslog",
#         "image": "",
#         "process": "rsyslogd",
#         "event": "security_file_open",
#         "dev_type": "",
#         "count": 10,
#     },
#     {
#         "pathname": "/var/log/auth.log",
#         "image": "",
#         "process": "rsyslogd",
#         "event": "security_file_open",
#         "dev_type": "",
#         "count": 6,
#     },
#     {
#         "pathname": "/var/log/kern.log",
#         "image": "",
#         "process": "rsyslogd",
#         "event": "security_file_open",
#         "dev_type": "",
#         "count": 8,
#     },
# ]

load_dotenv()


file_io_file = os.path.join(os.environ["PERFTEST_REPORTS_DIR"], "file_io_metrics.json")
with open(file_io_file) as f:
    data = json.load(f)


# Aggregate counts by directory
def aggregate_counts(data):
    directory_counts = defaultdict(int)
    directory_entries = defaultdict(list)

    for entry in data:
        directory = str(Path(entry["pathname"]).parent)
        directory_counts[directory] += entry["count"]
        directory_entries[directory].append(entry)

    return directory_counts, directory_entries


# Flatten the directory counts into a list of entries
def flatten_entries(directory_entries):
    flat_entries = []
    for directory, entries in directory_entries.items():
        if len(entries) == 1:
            flat_entries.append(entries[0])
        else:
            flat_entries.append(
                {
                    "pathname": f"{directory}/*",
                    "count": sum(entry["count"] for entry in entries),
                }
            )
    return flat_entries


# Calculate the total count
total_count = sum(entry["count"] for entry in data)
threshold_count = 0.8 * total_count

# Recursive aggregation
current_entries = data
all_entries = []

while True:
    directory_counts, directory_entries = aggregate_counts(current_entries)
    flat_entries = flatten_entries(directory_entries)
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
    print(f"{entry['pathname']}: {entry['count']}")


output_path = os.path.join(os.environ["PERFTEST_REPORTS_DIR"], "top_io.json")
print(output_path)
with open(output_path, "w") as f:
    json.dump(top_entries, f)
