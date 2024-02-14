#!/bin/bash

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)

_CALL_TEARDOWN=1
_N_RUNS=1

PROMETHEUS_ADDR=http://localhost:9090

DOS_DURATION_SEC=60
DOS_APP=/app/dos
DOS_N_FAKE_COMMANDS="2000"
DOS_MALICIOUS_COMMAND='echo 123 > /tmp/some_file && date && echo 123'

TRACEE_LISTEN_ADDR=http:/localhost:3366
TRACEE_CACHE_TYPE=mem
TRACEE_MEM_CACHE_SIZE=2048
TRACEE_DISK_CACHE_SIZE=1024*16

TRACEE_CACHE_PARAMS=()
if [[ "$TRACEE_CACHE_TYPE" == "mem" ]]; then
	TRACEE_CACHE_PARAMS+=("--cache")
	TRACEE_CACHE_PARAMS+=("cache-type=mem")
	TRACEE_CACHE_PARAMS+=("--cache")
	TRACEE_CACHE_PARAMS+=("mem-cache-size=$TRACEE_MEM_CACHE_SIZE")
else
	TRACEE_CACHE_PARAMS+=("--cache")
	TRACEE_CACHE_PARAMS+=("cache-type=hybrid")
	TRACEE_CACHE_PARAMS+=("--cache")
	TRACEE_CACHE_PARAMS+=("mem-cache-size=$TRACEE_MEM_CACHE_SIZE")
	TRACEE_CACHE_PARAMS+=("--cache")
	TRACEE_CACHE_PARAMS+=("disk-cache-size=$TRACEE_DISK_CACHE_SIZE")
fi

BENCHMARK_OUTPUT_FILE=""

clear_prometheus() {
	curl -X POST -g "$PROMETHEUS_ADDR/api/v1/admin/tsdb/delete_series?match[]=tracee_ebpf_lostevents_total"
	curl -X POST -g "$PROMETHEUS_ADDR/api/v1/admin/tsdb/delete_series?match[]=tracee_ebpf_events_total"
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

wait_tracee() {
	echo Waiting for tracee to start
	while
		! (curl -s "$TRACEE_LISTEN_ADDR/healthz" | grep -q "OK")
	do sleep 1; done
}

start_tracee() {
	echo Starting tracee container

	docker run --name tracee -d --rm --pid=host --cgroupns=host --privileged \
		-v $(pwd)/tracee:/etc/tracee -v /etc/os-release:/etc/os-release-host:ro \
		-p 3366:3366 tracee:latest --scope container --healthz=true --metrics --output none "${tracee_cache_params[@]}"
}

DOS_SLEEP_DURATION_SEC=0.015

# Parse command line options
# TODO: parametrize other dos options
while [[ "$#" -gt 0 ]]; do
	case $1 in
	--no_teardown) _CALL_TEARDOWN=0 ;; # If no_teardown is provided, disable teardown
	--output)
		shift
		OUTPUT_FILE=$1
		;;
	--sleep)
		shift
		DOS_DURATION_SEC=$1
		;;
	--n_runs)
		shift
		_N_RUNS=$1
		;;

	*) echo "Unknown option: $1" ;; # Optional: handle unknown options
	esac
	shift
done

start_dos() {
	# TODO: add building of dos container
	echo Starting dos container for $DOS_DURATION_SEC seconds

	docker run --rm -d --name dos dos $DOS_N_FAKE_COMMANDS "$DOS_MALICIOUS_COMMAND" $DOS_SLEEP_DURATION_SEC

	sleep $DOS_DURATION_SEC
}

wait_tracee_sink() {
	echo Waiting for tracee to sink events
	sleep 5
}

run_benchmark() {
	TRACEE_BENCH_CMD="go run $SCRIPT_DIR/../../cmd/tracee-bench/main.go --single=true --output json"

	$TRACEE_BENCH_CMD

	# if [ "$BENCHMARK_OUTPUT_FILE" != "" ]; then
	#
	# fi
}

run() {

	[[ $_CALL_TEARDOWN -eq 1 ]] && teardown

	tracee_is_running || start_tracee

	wait_tracee

	start_dos

	wait_tracee_sink

	$TRACEE_BENCH_CMD

	docker stop dos
	[[ $_CALL_TEARDOWN -eq 1 ]] && teardown
}

echo Running DoS "$_N_RUNS" times
for i in $(seq 1 $END); do
	run
done
