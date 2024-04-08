#!/bin/bash -ex

PROMETHEUS_ADDR=http://localhost:9090

DOS_SLEEP_DURATION_SEC=${DOS_SLEEP_DURATION_SEC:-0.016}
DOS_DURATION_SEC=60
DOS_CMD=/app/dos
DOS_N_FAKE_COMMANDS="2000"
DOS_MALICIOUS_COMMAND='>/tmp/some_file && date && echo 123'
# DOS_MALICIOUS_COMMAND='touch /tmp/counter && date && a="$(cat /tmp/counter)"; echo "$a +1" | bc > /tmp/counter'
DOS_CPU_LIMIT=${DOS_CPU_LIMIT:-".8"}
# DOS_CMD="while true; do cat /etc/passwd && date && sleep 0.2; done"
TRACEE_ROOT=$(git rev-parse --show-toplevel)
TRACEE_CACHE_TYPE=${TRACEE_CACHE_TYPE:-mem}
TRACEE_MEM_CACHE_SIZE=${TRACEE_MEM_CACHE_SIZE:-4096}
TRACEE_DISK_CACHE_SIZE=${TRACEE_DISK_CACHE_SIZE:-16384}
TRACEE_PERF_BUFFER_SIZE=${TRACEE_PERF_BUFFER_SIZE:-1024}
TRACEE_LISTEN_ADDR=http:/localhost:3366
TRACEE_EVENTS_SINK_TIMEOUT=${TRACEE_EVENTS_SINK_TIMEOUT:-5}
TRACEE_BENCHMARK_OUTPUT_FILE=${TRACEE_BENCHMARK_OUTPUT_FILE:-""}
TRACEE_LOG_FILE=${TRACEE_LOG_FILE:-/tmp/tracee/tracee.log}
TRACEE_EXE=/tracee/tracee-ebpf

call_teardown=0

tracee_cache_params=()
if [[ "$TRACEE_CACHE_TYPE" == "mem" ]]; then
	tracee_cache_params+=("--cache")
	tracee_cache_params+=("cache-type=mem")
	tracee_cache_params+=("--cache")
	tracee_cache_params+=("mem-cache-size=$TRACEE_MEM_CACHE_SIZE")
else
	tracee_cache_params+=("--cache")
	tracee_cache_params+=("cache-type=hybrid")
	tracee_cache_params+=("--cache")
	tracee_cache_params+=("mem-cache-size=$TRACEE_MEM_CACHE_SIZE")
	tracee_cache_params+=("--cache")
	tracee_cache_params+=("disk-cache-size=$TRACEE_DISK_CACHE_SIZE")
fi

start_prometheus() {
	perf_compose="$TRACEE_ROOT/performance/dashboard/docker-compose.yml"
	docker-compose -f "$perf_compose" up -d
}

clear_prometheus() {
	# curl -X POST -g "$PROMETHEUS_ADDR/api/v1/admin/tsdb/delete_series?match[]=tracee_ebpf_lostevents_total"
	# curl -X POST -g "$PROMETHEUS_ADDR/api/v1/admin/tsdb/delete_series?match[]=tracee_ebpf_events_total"

	# Set the match[] argument to "{}" to match all metrics
	MATCHERS='{}'
	curl -X POST "$PROMETHEUS_ADDR" -H "Content-Type: application/json" --data "{\"match[]\":[\"$MATCHERS\"]}"

}

tracee_is_running() {
	if [ -n "$(docker ps -q --filter "ancestor=tracee")" ]; then
		return 0 # True, container is found
	else
		return 1 # False, container is not found
	fi
}

# Teardown outdated instances of dos and tracee containers
teardown() {
	echo Tearing down existing tracee and dos containers
	docker stop tracee dos 2>/dev/null || true

	while [ $(tracee_is_running) ]; do
		sleep 0.1
	done

	clear_prometheus
}

start_tracee() {
	echo Starting tracee container

	# TODO: fix logging to file
	# --log-opt max-size=400m
	docker run --name tracee -d --rm --pid=host --cgroupns=host --privileged -e TRACEE_EXE=$TRACEE_EXE -v /run/docker.sock:/var/run/docker.sock \
		-v /tmp/tracee:/tmp/tracee -v /boot:/boot -v $(pwd)/tracee:/etc/tracee -v /etc/os-release:/etc/os-release-host:ro \
		-p 3366:3366 tracee:latest --scope container --healthz=true --metrics --output json --output out-file:${TRACEE_LOG_FILE} "${tracee_cache_params[@]}" \
		--perf-buffer-size="${TRACEE_PERF_BUFFER_SIZE}"

	echo Waiting for tracee to start
	while
		! (curl -s "$TRACEE_LISTEN_ADDR/healthz" | grep -q "OK")
	do sleep 1; done
}

run_dos() {
	# TODO: add building of dos container
	echo Starting dos container for $DOS_DURATION_SEC seconds
	# dos "$DOS_N_FAKE_COMMANDS" "$DOS_MALICIOUS_COMMAND" "$DOS_SLEEP_DURATION_SEC"
	# --cpus "$DOS_CPU_LIMIT"
	docker run -d --rm --name dos \
		-e DOS_CMD="$DOS_CMD" \
		-e DOS_N_FAKE_COMMANDS="$DOS_N_FAKE_COMMANDS" \
		-e DOS_MALICIOUS_COMMAND="$DOS_MALICIOUS_COMMAND" \
		-e DOS_SLEEP_DURATION_SEC="$DOS_SLEEP_DURATION_SEC" dos

	sleep $DOS_DURATION_SEC

	docker kill dos 2>/dev/null || true
}

wait_tracee_sink() {
	echo Waiting for tracee to sink events
	sleep "$TRACEE_EVENTS_SINK_TIMEOUT"
}

run_benchmark() {
	TRACEE_BENCH_CMD="go run $TRACEE_ROOT/cmd/tracee-bench/main.go --single=true --output json"
	$TRACEE_BENCH_CMD
}

_main() {

	# [[ $call_teardown -eq 1 ]] && teardown

	start_prometheus
	clear_prometheus

	tracee_is_running || start_tracee

	run_dos

	wait_tracee_sink

	docker stop tracee

	if [ "$TRACEE_BENCHMARK_OUTPUT_FILE" != "" ]; then
		benchmark_dir=${TRACEE_BENCHMARK_OUTPUT_FILE%/*}
		mkdir -p "$benchmark_dir"
		run_benchmark >"$TRACEE_BENCHMARK_OUTPUT_FILE"
	else
		run_benchmark
	fi

	# [[ $call_teardown -eq 1 ]] && teardown
}

_main
