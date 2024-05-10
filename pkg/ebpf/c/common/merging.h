#ifndef __COMMON_MERGING_H__
#define __COMMON_MERGING_H__

#include <types.h>
#include <common/logging.h>
#include <common/common.h>
#include <bpf/bpf_tracing.h>

// PROTOTYPES

statfunc bool should_merge_event(u64 timestamp, merge_stats_t *merge_stats);
statfunc merge_stats_t *init_io_merge_stats(file_io_key_t *io_key, u64 timestamp);
statfunc merge_stats_t *init_open_merge_stats(file_open_key_t *open_key, u64 timestamp);

// FUNCTIONS

#define SUBMIT_INTERVAL 30000000000 // 30s

statfunc bool should_merge_event(u64 timestamp, merge_stats_t *stats)
{
    bool merge_needed = 1;

    if ((timestamp - stats->last_seen_time) > (u64) SUBMIT_INTERVAL) {
        merge_needed = 0;
    }

    stats->last_seen_time = timestamp;
    return merge_needed;
}

statfunc merge_stats_t *init_io_merge_stats(file_io_key_t *io_key, u64 timestamp)
{
    merge_stats_t stats = {};
    __builtin_memset(&stats, 0, sizeof(stats));

    stats.last_seen_time = timestamp;

    bpf_map_update_elem(&file_io_map, io_key, &stats, BPF_NOEXIST);
    return bpf_map_lookup_elem(&file_io_map, io_key);
}

statfunc merge_stats_t *init_open_merge_stats(file_open_key_t *open_key, u64 timestamp)
{
    merge_stats_t stats = {};
    __builtin_memset(&stats, 0, sizeof(stats));

    stats.last_seen_time = timestamp;

    bpf_map_update_elem(&file_open_map, open_key, &stats, BPF_NOEXIST);
    return bpf_map_lookup_elem(&file_open_map, open_key);
}

#endif
