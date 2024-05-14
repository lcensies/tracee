from dotenv import load_dotenv
import json
from os import environ
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.ticker import FormatStrFormatter, StrMethodFormatter

import matplotlib.lines as lines
import matplotlib.patches as patches
import matplotlib.text as text

load_dotenv()
assert "TRACEE_MEMORY_STATS_FILE" in environ
assert "TRACEE_CACHE_STATS_FILE" in environ


def load_json(path: str):
    assert type(path) == str
    with open(path, "r") as f:
        return json.load(f)


def get_relative_ts(data: list[list]) -> list[float]:
    return [float(x[0]) - float(data[0][0]) for x in data]


def get_tracee_cache_load() -> tuple[list[float], list[float]]:
    cache_stats_path = environ.get(
        "TRACEE_CACHE_STATS_FILE", "/tmp/tracee/events_cache_metrics.json"
    )
    raw_stats = load_json(cache_stats_path)
    data = [x["values"] for x in raw_stats][0]
    timestamps = get_relative_ts(data)
    load_stats = [float(x[1]) for x in data]
    return timestamps, load_stats


def get_tracee_mem_stats() -> tuple[list[float], list[float]]:
    mem_stats_path = environ.get(
        "TRACEE_MEMORY_STATS_FILE", "/tmp/tracee/agent_memory_metrics.json"
    )
    raw_stats = load_json(mem_stats_path)
    data = [
        x["values"]
        for x in raw_stats["data"]["result"]
        if x["metric"]["job"] == "tracee"
    ][0]

    # print(data)
    def bytes_to_mb(num: int) -> float:
        return num / 1024 / 1024

    timestamps = get_relative_ts(data)
    mem_consumption_mb = [bytes_to_mb(int(x[1])) for x in data]
    return (timestamps, mem_consumption_mb)


mem_stats_timestamps, mem_stats_mb = get_tracee_mem_stats()
cache_load_timestamps, cache_load = get_tracee_cache_load()

# plt.plot(mem_stats_timestamps, mem_stats_mb)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

ax1.plot(mem_stats_timestamps, mem_stats_mb)

# ax1.set_title("Agent memory consumption")
ax1.set_xlabel("Time (seconds)")
ax1.set_ylabel("Agent memory consumption (MB)")

ax2.plot(cache_load_timestamps, [round(float(x), 2) for x in cache_load])
# ax2.yaxis.set_major_formatter(FormatStrFormatter("%.2f"))
# ax2.yaxis.set_major_formatter(StrMethodFormatter("{x:,.2f}"))
ax2.set_xlabel("Time (seconds)")
ax2.set_ylabel("Cache load (rate)")


def print_stats():
    mem_median = np.median(np.array(mem_stats_mb[0:-4]))
    print(f"Median memory consumption: {mem_median}")
    print(cache_load_timestamps)
    print(cache_load)


# 5 seconds sampled intervals, 20 seconds
# sleep, so we take -4 index
div_x = cache_load_timestamps[-4]
div_y_low = 0
div_y_high = 1

min_y = min(mem_stats_mb)
max_y = max(mem_stats_mb)

x1, y1 = [div_x, div_x], [min_y, max_y]
ax1.plot(x1, y1, marker="o")


load_caption = "Load test finish"
load_caption = "Load stop"
scale = (max_y - min_y) * 0.05

offset = 9

ax1.text(div_x - offset, min_y + scale, load_caption, fontsize=10)


min_y = min(cache_load)
max_y = max(cache_load)

scale = (max_y - min_y) * 0.05

x1, y1 = [div_x, div_x], [0, 1]
ax2.plot(x1, y1, marker="o")
ax2.text(div_x - offset, min_y + scale, load_caption, fontsize=9)

# ax2.annotate(
#     load_caption,
#     xy=(div_x, 0),
#     fontsize=10,
#     # xytext=(div_x + 1, 0),
#     # arrowprops=dict(facecolor="red"),
#     # color="g",
# )


print_stats()


plt.savefig("mem_consumption.png")

# plt.savefig("cache_load.png")
plt.tight_layout()
plt.show()
