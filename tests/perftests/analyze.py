from dotenv import load_dotenv
import json
from os import environ

import matplotlib.pyplot as plt
import matplotlib

load_dotenv()


def load_json(path: str):
    assert type(path) == str
    with open(path, "r") as f:
        return json.load(f)


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

    timestamps = [float(x[0]) - float(data[0][0]) for x in data]
    mem_consumption_mb = [bytes_to_mb(int(x[1])) for x in data]
    return (timestamps, mem_consumption_mb)


# print(environ)

assert "TRACEE_MEMORY_STATS_FILE" in environ
# print(environ["TRACEE_MEMORY_STATS_FILE"])

mem_stats_timestamps, mem_stats_mb = get_tracee_mem_stats()

print(mem_stats_timestamps)

# matplotlib.use("PyQT6")
# matplotlib.use("QtAgg")
plt.plot(mem_stats_timestamps, mem_stats_mb)


# plt.title("Agent memory consumption")
plt.xlabel("Time")
plt.ylabel("Agent memory consumption (MB)")

# axes = plt.axes()
# axes.set_xlim([0, 120])

plt.savefig("mem_consumption.png")
plt.show()
