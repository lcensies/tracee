from dotenv import load_dotenv
import json
from scipy.interpolate import make_interp_spline, BSpline
import shutil
from os import environ
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from dataclasses import dataclass
import pandas as pd
from dataclasses import field
from pathlib import Path
from datetime import datetime

# import perfplot

load_dotenv()

div_x_idx = -1

# load_caption = "Load test finish"
load_caption = "Load\nstop"

# TODO: average
PERFTEST_REPORTS_DIR = f"{environ['PERFTEST_REPORTS_DIR']}/1/tracee"
print(PERFTEST_REPORTS_DIR)
REPORT_SUMMARY_FILE = f"{PERFTEST_REPORTS_DIR}/summary.json"


# TODO: change to single file
MEMORY_STATS_FILE = "agent_memory_metrics.json"
EVENTS_RATE_STATS_FILENAME = "events_rate_metrics.json"
LOST_EVENTS_STATS_FILENAME = "events_lost_metrics.json"
CACHED_EVENTS_STATS_FILENAME = "events_cached_metrics.json"
CACHE_LOAD_STATS_FILENAME = "cache_load_metrics.json"


def get_events_file(output_dir) -> str:
    return f"{output_dir}/{EVENTS_RATE_STATS_FILENAME}"


def get_lost_events_file(output_dir) -> str:
    return f"{output_dir}/{LOST_EVENTS_STATS_FILENAME}"


def get_cached_events_file(output_dir) -> str:
    return f"{output_dir}/{CACHED_EVENTS_STATS_FILENAME}"


def get_memory_stats_file(output_dir) -> str:
    return f"{output_dir}/{MEMORY_STATS_FILE}"


def get_cache_load_file(output_dir) -> str:
    return f"{output_dir}/{CACHE_LOAD_STATS_FILENAME}"


def json_to_csv(file):
    with open(file, encoding="utf-8") as inputfile:
        df = pd.read_json(inputfile)

    csv_filename = file.replace("json", "csv")
    df.to_csv(csv_filename, encoding="utf-8", index=False)


@dataclass
class BenchmarkResult:
    label: str
    output_dir: str

    events_captured: int = -1
    mem_consumption_median: int = -1
    events_lost: int = -1
    events_cached: int = -1

    # TODO: change to numpy arr
    events_rate: list = field(default_factory=list)
    events_rate_ts: list = field(default_factory=list)

    lost_events_rate: list = field(default_factory=list)
    lost_events_rate_ts: list = field(default_factory=list)

    cache_load: list = field(default_factory=list)
    cache_load_ts: list = field(default_factory=list)

    mem_consumption: list = field(default_factory=list)
    mem_consumption_ts: list = field(default_factory=list)

    def __post_init__(self):
        self.output_dir = self.output_dir + "/tracee"

        ev_rate_file = get_events_file(self.output_dir)
        self.events_rate, self.events_rate_ts, self.events_captured = load_events_rate(
            ev_rate_file
        )

        lost_events_file = get_lost_events_file(self.output_dir)
        (
            self.lost_events_rate_ts,
            self.lost_events_rate,
            self.events_lost,
        ) = load_lost_events_rate(lost_events_file)

        cache_load_file = get_cache_load_file(self.output_dir)
        self.cache_load_ts, self.cache_load = load_cache_load(cache_load_file)

        cache_load_file = get_cached_events_file(self.output_dir)
        events_cached_ts, events_cached = load_cached_events(cache_load_file)
        self.events_cached = int(events_cached[div_x_idx])

        mem_consumption_file = get_memory_stats_file(self.output_dir)
        (
            self.mem_consumption_ts,
            self.mem_consumption,
            self.mem_consumption_median,
        ) = load_tracee_mem_stats(mem_consumption_file)


def load_json(path: str):
    assert type(path) == str

    Path(REPORT_SUMMARY_FILE).touch(exist_ok=True)

    with open(path, "r+") as f:
        try:
            obj = json.load(f)
        except Exception:
            obj = {}
        return obj


def save_json(obj, path: str):
    with open(path, "w+") as f:
        json.dump(obj, f)


def get_test_ticks():
    start_time_path = f"{PERFTEST_REPORTS_DIR}/test_start_time.json"
    end_time_path = f"{PERFTEST_REPORTS_DIR}/test_end_time.json"

    start_time = datetime.strptime(
        load_json(start_time_path)["start_time"], "%Y-%m-%dT%H:%M:%S"
    )
    end_time = datetime.strptime(
        load_json(end_time_path)["end_time"], "%Y-%m-%dT%H:%M:%S"
    )
    return start_time, end_time


def get_relative_ts(data: list[list]) -> list[float]:
    return [float(x[0]) - float(data[0][0]) for x in data]


def load_tracee_mem_stats(
    mem_stats_path=f"{PERFTEST_REPORTS_DIR}/{MEMORY_STATS_FILE}",
) -> tuple[list[float], list[float], int]:
    raw_stats = load_json(mem_stats_path)
    data = [
        x["values"]
        for x in raw_stats["data"]["result"]
        if x["metric"]["job"] == "tracee"
    ][0]

    def bytes_to_mb(num: int) -> float:
        return num / 1024 / 1024

    timestamps = get_relative_ts(data)
    mem_consumption_mb = [bytes_to_mb(int(x[1])) for x in data]
    mem_consumption_median = np.median(mem_consumption_mb)
    return (timestamps, mem_consumption_mb, int(mem_consumption_median))


def get_ev_inc_rate(timestamps, events) -> tuple[list[float], list[float]]:
    pass
    ts_diff = timestamps[1] - timestamps[0]

    rates: list[float] = []
    for i in range(len(events) - 1):
        inc_per_ts = (int(events[i + 1]) - int(events[i])) / ts_diff
        rates.append(inc_per_ts)

    return (timestamps[1:], rates)


def reduce_series_by_ts(timestamps, values, interval=5):
    assert len(timestamps) == len(values)

    ts_reduced = [timestamps[0]]
    values_reduced = [values[0]]

    cur_ts = timestamps[0]

    for ts, val in zip(timestamps, values):
        if ts - cur_ts >= interval:
            ts_reduced.append(ts)
            values_reduced.append(val)
            cur_ts = ts

    return ts_reduced, values_reduced


def load_series(path: str, value_type=float):
    raw_stats = load_json(path)
    if type(raw_stats) == list:
        raw_stats = raw_stats[0]
    data = [x["values"] for x in raw_stats["data"]["result"]][0]

    timestamps = get_relative_ts(data)
    values = [value_type(x[1]) for x in data]

    return timestamps, values


# TODO: change to single file
def load_events(path=f"{PERFTEST_REPORTS_DIR}/{EVENTS_RATE_STATS_FILENAME}"):
    return load_series(path, int)


def load_lost_events(path=f"{PERFTEST_REPORTS_DIR}/{LOST_EVENTS_STATS_FILENAME}"):
    return load_series(path, int)


def load_cache_load(path=f"{PERFTEST_REPORTS_DIR}/{CACHE_LOAD_STATS_FILENAME}"):
    return load_series(path)


def load_cached_events(path=f"{PERFTEST_REPORTS_DIR}/{CACHED_EVENTS_STATS_FILENAME}"):
    return load_series(path, int)


def add_div_tick(ax, div_value, label, axis="x"):
    def get_tick_idx(ticks, lim):
        for i, x in enumerate(ticks):
            if lim < x:
                return i

    if axis == "x":
        ticks = ax.get_xticks()

        labels = [item.get_text() for item in ax.get_xticklabels()]
        tick_idx = get_tick_idx(ticks, float(div_value))

        labels[tick_idx] = f"{labels[tick_idx]}\n{label}"

        ax.set_xticks(ticks)
        ax.set_xticklabels(labels)
    else:
        ticks = ax.get_yticks()

        labels = [item.get_text() for item in ax.get_yticklabels()]
        tick_idx = get_tick_idx(ticks, float(div_value))

        labels[tick_idx] = f"{labels[tick_idx]}\n{label}"

        ax.set_yticks(ticks)
        ax.set_yticklabels(labels)


def filter_gt_zero(timestamps, values):
    assert len(timestamps) == len(values)

    idxs_lt_zero = [i for i in range(len(timestamps)) if values[i] < 0]
    ts_filtered = np.delete(timestamps, idxs_lt_zero)
    values_filtered = np.delete(values, idxs_lt_zero)

    return ts_filtered, values_filtered


def filter_start_inc(timestamps, values):
    assert len(timestamps) == len(values)

    inc_idx = 0
    for i in range(len(values) - 1):
        if values[i] < values[i + 1]:
            inc_idx = i
            break

    return timestamps[inc_idx:], values[inc_idx:]


def get_load_stop_ts(timestamps, load_finish_sec=environ.get("POST_TEST_SLEEP_SEC", 0)):
    ts_limit = timestamps[-1] - load_finish_sec
    for i, ts in enumerate(timestamps):
        # if ts is None:
        #     continue
        if ts >= ts_limit:
            return i, ts
    return len(timestamps) - 1, timestamps[-1]


def interpolate(timestamps, values, n_points=60):
    spl = make_interp_spline(timestamps, values, k=3)  # type: BSpline
    ts_int = np.linspace(timestamps[0], timestamps[-1], n_points)
    values_int = spl(ts_int)
    return ts_int, values_int


def align_series(ref_timestamps, timestamps, values):
    return timestamps[: len(ref_timestamps)], values[: len(timestamps)]


def save_plot(pic_name: str = "events.png", copy=True):
    EVENTS_PLOT_FILENAME = pic_name
    plt.savefig(EVENTS_PLOT_FILENAME, bbox_inches="tight")
    if copy:
        shutil.copy(
            Path(EVENTS_PLOT_FILENAME), f"{PERFTEST_REPORTS_DIR}/{EVENTS_PLOT_FILENAME}"
        )


def load_events_rate(path) -> tuple[list, list, int]:
    events_ts, events = load_events(path)
    ev_rate_ts, ev_rate = get_ev_inc_rate(events_ts, events)
    ev_rate_ts, ev_rate = reduce_series_by_ts(ev_rate_ts, ev_rate, 2)
    return ev_rate_ts, ev_rate, int(events[div_x_idx])


def load_lost_events_rate(path) -> tuple[list, list, int]:
    lost_events_ts, lost_events = load_lost_events(path)
    lost_events_ts, lost_events_rate = get_ev_inc_rate(lost_events_ts, lost_events)
    return lost_events_ts, lost_events_rate, int(lost_events[-1])


def show_all():
    global div_x_idx
    fig, subplots = plt.subplots(2, 2, figsize=(10, 5))
    ((ax1, ax2), (ax3, ax4)) = subplots

    ax1.set_xlabel("Time (seconds)")
    ax1.set_ylabel("Events (rate)")

    ax2.set_xlabel("Time (seconds)")
    ax2.set_ylabel("Lost events (increase rate)")

    # events

    events_ts, events = load_events()
    # events_ts, events = interpolate(events_ts, events)
    # events_ts, events = reduce_series_by_ts(events_ts, events)

    ev_rate_ts, ev_rate = get_ev_inc_rate(events_ts, events)
    ev_rate_ts, ev_rate = reduce_series_by_ts(ev_rate_ts, ev_rate, 2)

    ax1.set_xlim([0, ev_rate_ts[-1]])
    ax2.set_xlim([0, ev_rate_ts[-1]])
    ax3.set_xlim([0, ev_rate_ts[-1]])
    # ax4.set_xlim([0, ev_rate_ts[-1]])
    ax4.set_ylim([0, 1.01])

    # lost events

    lost_events_ts, lost_events = load_lost_events()
    lost_events_ts, lost_events_rate = get_ev_inc_rate(lost_events_ts, lost_events)

    ax1.plot(ev_rate_ts, ev_rate)
    ax1.set(yscale="symlog")
    ax2.plot(lost_events_ts, lost_events_rate)

    # div_x_idx, div_x = get_load_stop_ts(ev_rate_ts)
    # add_div_tick(ax1, div_x, load_caption)
    # add_div_tick(ax2, div_x, load_caption)

    plt.tight_layout()

    # Memory
    mem_stats_timestamps, mem_stats_mb = load_tracee_mem_stats()
    mem_consumption_median = np.median(mem_stats_mb)
    mem_stats_timestamps, mem_stats_mb = interpolate(
        mem_stats_timestamps, mem_stats_mb, 60
    )
    cache_load_timestamps, cache_load = load_cache_load()

    events_cached_ts, events_cached = load_cached_events()

    # fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    # fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 5))

    ax3.plot(mem_stats_timestamps, mem_stats_mb)

    ax3.set_xlabel("Time (seconds)")
    ax3.set_ylabel("Agent memory consumption (MB)")

    ax4.plot(cache_load_timestamps, [round(float(x), 2) for x in cache_load])
    ax4.set_xlabel("Time (seconds)")
    ax4.set_ylabel("Cache load (rate)")

    # add_div_tick(ax3, div_x, load_caption)
    # add_div_tick(ax4, div_x, load_caption)

    save_plot()

    # MEM_PLOT_PNG = "mem_consumption.png"
    # plt.savefig(MEM_PLOT_PNG, bbox_inches="tight")
    # shutil.copy(Path(MEM_PLOT_PNG), f"{PERFTEST_REPORTS_DIR}/{MEM_PLOT_PNG}")

    def update_summary() -> dict:
        summary = {}
        summary["events_captured"] = events[div_x_idx] + events_cached[div_x_idx]
        summary["events_lost"] = lost_events[div_x_idx]
        summary["memory_consumption_median_mb"] = mem_consumption_median
        return summary

    summary = update_summary()
    save_json(summary, REPORT_SUMMARY_FILE)
    return summary


def get_bench_summary_comparison(is_reversed=False, *results: BenchmarkResult) -> dict:
    if not is_reversed:
        summary = {"results": []}
        for res in results:
            res_json = {
                "implementation": res.label,
                "events_captured": res.events_captured + res.events_cached,
                "events_lost": res.events_lost,
                "memory_consumption_median_mb": res.mem_consumption_median,
            }
            summary["results"].append(res_json)
    else:
        summary = {
            "Implementation": [],
            "Events Captured": [],
            "Events Lost": [],
            "Median Memory Consumption (MB)": [],
        }

        for res in results:
            summary["Implementation"].append(res.label)
            summary["Events Captured"].append(res.events_captured + res.events_cached)
            summary["Events Lost"].append(res.events_lost)
            summary["Median Memory Consumption (MB)"].append(res.mem_consumption_median)

    return summary


def compare_results(first: BenchmarkResult, second: BenchmarkResult):
    global div_x_idx

    fig, subplots = plt.subplots(2, 2, figsize=(10, 5))
    ((ax1, ax2), (ax3, ax4)) = subplots

    ax1.set_xlabel("Time (seconds)")
    ax1.set_ylabel("Events (rate)")
    ax1.set(yscale="symlog")

    ax2.set_xlabel("Time (seconds)")
    ax2.set_ylabel("Lost events (increase rate)")

    ax3.set_xlabel("Time (seconds)")
    ax3.set_ylabel("Agent memory consumption (MB)")

    ax4.set_xlabel("Time (seconds)")
    ax4.set_ylabel("Cache load (rate)")

    ev_range = [0, first.events_rate[-1]]
    ax1.set_xlim(ev_range)
    ax2.set_xlim(ev_range)
    ax3.set_xlim(ev_range)
    ax4.set_xlim(ev_range)
    # ax4.set_ylim([0, 1.01])

    ax1.plot(
        first.events_rate,
        first.events_rate_ts,
        label=first.label,
        color="red",
    )

    ax1.plot(
        second.events_rate,
        second.events_rate_ts,
        label=second.label,
        color="blue",
    )

    ax2.plot(
        first.lost_events_rate,
        first.lost_events_rate_ts,
        label=first.label,
        color="red",
    )

    ax2.plot(
        second.lost_events_rate,
        second.lost_events_rate_ts,
        label=second.label,
        color="blue",
    )

    ax3.plot(
        first.mem_consumption_ts,
        first.mem_consumption,
        label=first.label,
        color="red",
    )

    y_div = int(min(np.max(first.mem_consumption), np.max(second.mem_consumption)))
    add_div_tick(ax3, y_div, str(y_div), "y")

    ax3.plot(
        second.mem_consumption_ts,
        second.mem_consumption,
        label=second.label,
        color="blue",
    )

    ax4.plot(
        first.cache_load_ts,
        first.cache_load,
        label=first.label,
        color="red",
    )
    ax4.plot(
        second.cache_load_ts,
        second.cache_load,
        label=second.label,
        color="blue",
    )

    ax1.legend()
    ax2.legend()
    ax3.legend()
    ax4.legend()

    plt.tight_layout()

    save_plot(copy=False)
    comparison_filename = "comparison.json"

    # Dirty workaround to
    # TODO: refactor
    summary = get_bench_summary_comparison(True, first, second)
    save_json(summary, comparison_filename)
    json_to_csv(comparison_filename)

    summary = get_bench_summary_comparison(False, first, second)
    save_json(summary, comparison_filename)


def show_cache():
    print("show_cache")
    cache_load_timestamps, cache_load = load_cache_load()

    plt.plot(cache_load_timestamps, [round(float(x), 2) for x in cache_load])
    ax = plt.gca()
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Cache load (rate)")
    save_plot("cache.png")


# TODO: parametrize


def cmp_pgbench_default():
    first = BenchmarkResult("baseline", f"{environ['EXPERIMENTS_DIR']}/1-4-base-60s")
    second = BenchmarkResult(
        "merging", f"{environ['EXPERIMENTS_DIR']}/3-2-merging-no-sleep"
    )
    compare_results(first, second)


def cmp_pgbench_gen():
    first = BenchmarkResult("baseline", f"{environ['EXPERIMENTS_DIR']}/1-4-base-60s")
    second = BenchmarkResult(
        "merging", f"{environ['EXPERIMENTS_DIR']}/3-2-merging-no-sleep"
    )
    compare_results(first, second)


cmp_pgbench_default()
