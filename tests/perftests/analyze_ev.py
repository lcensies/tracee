from dotenv import load_dotenv
import json
from scipy.interpolate import make_interp_spline, BSpline
from os import environ
import numpy as np
import matplotlib.pyplot as plt
import matplotlib

load_dotenv()

# load_caption = "Load test finish"
load_caption = "Load\nstop"


EVENTS_RATE_STATS_FILENAME = "events_rate_metrics.json"
LOST_EVENTS_STATS_FILENAME = "events_lost_metrics.json"


def load_json(path: str):
    assert type(path) == str
    with open(path, "r") as f:
        return json.load(f)


def get_relative_ts(data: list[list]) -> list[float]:
    return [float(x[0]) - float(data[0][0]) for x in data]


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


def load_series(path: str):
    raw_stats = load_json(path)
    data = [x["values"] for x in raw_stats["data"]["result"]][0]
    timestamps = get_relative_ts(data)
    values = [int(x[1]) for x in data]

    return timestamps, values


def load_events():
    path = f"{environ['PERFTEST_REPORTS_DIR']}/{EVENTS_RATE_STATS_FILENAME}"
    return load_series(path)


def load_lost_events():
    path = f"{environ['PERFTEST_REPORTS_DIR']}/{LOST_EVENTS_STATS_FILENAME}"
    return load_series(path)


def add_div_tick(ax, div_value, label):
    def get_tick_idx(ticks, lim):
        for i, x in enumerate(ticks):
            if lim < x:
                return i

    ticks = ax.get_xticks()

    labels = [item.get_text() for item in ax.get_xticklabels()]
    tick_idx = get_tick_idx(ticks, float(div_value))

    labels[tick_idx] = f"{labels[tick_idx]}\n{label}"

    ax.set_xticks(ticks)
    ax.set_xticklabels(labels)


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


def get_load_stop_ts(timestamps, load_finish_sec=20):
    ts_limit = timestamps[-1] - load_finish_sec
    for ts in timestamps:
        if ts >= ts_limit:
            return ts


# plt.plot(mem_stats_timestamps, mem_stats_mb)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

ax1.set_xlabel("Time (seconds)")
ax1.set_ylabel("Events per-second increase rate")

ax2.set_xlabel("Time (seconds)")
ax2.set_ylabel("Lost events (rate)")


# def print_stats():
#     mem_median = np.median(np.array(mem_stats_mb[0:-4]))
#     print(f"Median memory consumption: {mem_median}")
#     print(cache_load_timestamps)
#     print(cache_load)

# events

events_ts, events = load_events()
events_ts, events = reduce_series_by_ts(events_ts, events)
events_ts_int = np.linspace(events_ts[0], events_ts[-1], 60)


ev_rate_ts, ev_rate = get_ev_inc_rate(events_ts, events)

spl = make_interp_spline(ev_rate_ts, ev_rate, k=3)  # type: BSpline
ev_rate_int = spl(events_ts_int)

events_ts_int, ev_rate_int = filter_gt_zero(events_ts_int, ev_rate_int)
events_ts_int, ev_rate_int = filter_start_inc(events_ts_int, ev_rate_int)

ax1.set_xlim([0, ev_rate_ts[-1]])
ax2.set_xlim([0, ev_rate_ts[-1]])

div_x = get_load_stop_ts(ev_rate_ts)
add_div_tick(ax1, div_x, load_caption)
add_div_tick(ax2, div_x, load_caption)


# lost events

lost_events_ts, lost_events = load_lost_events()
lost_events_ts, lost_events_rate = get_ev_inc_rate(lost_events_ts, lost_events)

# spl = make_interp_spline(lost_events_ts, lost_events_rate, k=3)  # type: BSpline
# lost_events_ts_int = np.linspace(lost_events_ts[0], lost_events_ts[-1], 60)
# lost_events_rate_int = spl(lost_events_ts_int)

ax1.plot(events_ts_int, ev_rate_int)
ax2.plot(lost_events_ts, lost_events_rate)

plt.savefig("events.png")

# plt.savefig("cache_load.png")
plt.tight_layout()
plt.show()


# TODO: compare with perfplot
# https://pypi.org/project/perfplot/
