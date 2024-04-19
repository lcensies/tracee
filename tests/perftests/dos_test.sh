#!/bin/bash -ex
PROMETHEUS_ADDR=http://localhost:9090

DOCKER_INTERACTIVE_FLAG=-d

DOS_SLEEP_DURATION_SEC=${DOS_SLEEP_DURATION_SEC:-0.05}
DOS_DURATION_SEC=${DOS_DURATION_SEC:-120}
DOS_CMD=/app/dos
DOS_N_FAKE_COMMANDS="2000"
DOS_MALICIOUS_COMMAND='>/tmp/some_file && date && echo 123'
# DOS_MALICIOUS_COMMAND='touch /tmp/counter && date && a="$(cat /tmp/counter)"; echo "$a +1" | bc > /tmp/counter'
DOS_CPU_LIMIT=${DOS_CPU_LIMIT:-"0.8"}
# DOS_CMD="while true; do cat /etc/passwd && date && sleep 0.2; done"
TRACEE_CPU_LIMIT=${TRACEE_CPU_LIMIT:-"1"}
TRACEE_NO_CONTAINER=false
TRACEE_ROOT=$(git rev-parse --show-toplevel)
TRACEE_CACHE_TYPE=${TRACEE_CACHE_TYPE:-mem}
TRACEE_CACHE_STAGE="before-decode"
TRACEE_MEM_CACHE_SIZE=${TRACEE_MEM_CACHE_SIZE:-1024}
# TRACEE_MEM_CACHE_SIZE=${TRACEE_MEM_CACHE_SIZE:-512}
TRACEE_DISK_CACHE_SIZE=${TRACEE_DISK_CACHE_SIZE:-16384}
TRACEE_PERF_BUFFER_SIZE=${TRACEE_PERF_BUFFER_SIZE:-1024}
TRACEE_LISTEN_ADDR=http:/localhost:3366
TRACEE_EVENTS_SINK_TIMEOUT=${TRACEE_EVENTS_SINK_TIMEOUT:-5}
TRACEE_BENCHMARK_OUTPUT_FILE=${TRACEE_BENCHMARK_OUTPUT_FILE:-""}
TRACEE_LOG_FILE=${TRACEE_LOG_FILE:-/tmp/tracee/tracee.log}
TRACEE_EXE=/tracee/tracee-ebpf
TRACEE_EVENTS=security_file_open
# --output out-file:/tmp/tracee/tracee.log -
# TRACEE_EVENTS=security_file_open,creat,chmod,fchmod,chown,fchown,lchown,ptrace,setuid,setgid,setpgid,setsid,setreuid,setregid,setresuid,setresgid,setfsuid,setfsgid,init_module,fchownat,fchmodat,setns,process_vm_readv,process_vm_writev,finit_module,memfd_create,move_mount,sched_process_exec,security_inode_unlink,security_socket_connect,security_socket_accept,security_socket_bind,security_sb_mount,net_packet_icmp,net_packet_icmpv6,net_packet_dns_request,net_packet_dns_response,net_packet_http_request,net_packet_http_response
TRACEE_CACHE_FLAGS="--cache cache-stage=$TRACEE_CACHE_STAGE --cache cache-type=$TRACEE_CACHE_TYPE --cache mem-cache-size=$TRACEE_MEM_CACHE_SIZE"
# TRACE_LOG_FLAGS="--log debug --log file:${TRACEE_LOG_FILE"
TRACE_LOG_FLAGS=""

TRACEE_OUTPUT_FILE="/tmp/tracee/output.json"
# TRACEE_OUTPUT_FLAGS="--output json --output out-file:${TRACEE_OUTPUT_FILE}"
TRACEE_OUTPUT_FLAGS="--output none"

TRACEE_FLAGS="$TRACEE_LOG_FLAGS $TRACEE_OUTPUT_FLAGS $TRACEE_CACHE_FLAGS --metrics --healthz=true  -e ${TRACEE_EVENTS}"

call_teardown=0

start_prometheus() {
	perf_compose="$TRACEE_ROOT/performance/dashboard/docker-compose.yml"
	docker-compose -f "$perf_compose" up -d
}

clear_prometheus() {
	# curl -X POST -g "$PROMETHEUS_ADDR/api/v1/admin/tsdb/delete_series?match[]=tracee_ebpf_lostevents_total"
	# curl -X POST -g "$PROMETHEUS_ADDR/api/v1/admin/tsdb/delete_series?match[]=tracee_ebpf_events_total"

	perf_compose="$TRACEE_ROOT/performance/dashboard/docker-compose.yml"
	docker-compose -f "$perf_compose" down
	docker volume rm dashboard_prometheus_data 2>/dev/null || :

	# Set the match[] argument to "{}" to match all metrics
	# MATCHERS='{}'
	# curl -X POST "$PROMETHEUS_ADDR/api/v1/admin/tsdb/delete_series" -H "Content-Type: application/json" --data "{\"match[]\":[\"$MATCHERS\"]}"

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
	echo Starting tracee

	if [ "${TRACEE_NO_CONTAINER}" = true ]; then
		TRACEE_CMD="sudo ./dist/tracee"
	else
		TRACEE_CMD="docker run --cpus ${TRACEE_CPU_LIMIT} --name tracee -e TRACEE_EXE=/tracee/tracee-ebpf ${DOCKER_INTERACTIVE_FLAG} --rm --pid=host --cgroupns=host --privileged -v /etc/os-release:/etc/os-release-host:ro -v /boot:/boot -v /var/run:/var/run:ro -v /tmp/tracee:/tmp/tracee -p 3366:3366 tracee:latest"
	fi

	echo TRACEE_CMD is "$TRACEE_CMD"
	$TRACEE_CMD $TRACEE_FLAGS

	# docker run --name tracee -d --rm --pid=host --cgroupns=host --privileged -e TRACEE_EXE=$TRACEE_EXE -v /run/docker.sock:/var/run/docker.sock \
	# 	-v /var/run:/var/run:ro -v /tmp/tracee:/tmp/tracee -v /boot:/boot -v $(pwd)/tracee:/etc/tracee -v /etc/os-release:/etc/os-release-host:ro -e "${TRACEE_EVENTS}" \
	# 	-p 3366:3366 tracee:latest --healthz=true --metrics --output json --output out-file:${TRACEE_LOG_FILE} "${tracee_cache_params[@]}" \
	# 	--perf-buffer-size="${TRACEE_PERF_BUFFER_SIZE}"

	# -o option:sort-events # --proctree source=events

	echo Waiting for tracee to start
	while
		! (curl -s "$TRACEE_LISTEN_ADDR/healthz" | grep -q "OK")
	do sleep 1; done
}

run_dos() {
	# TODO: add building of dos container
	echo Starting dos container for $DOS_DURATION_SEC seconds
	# dos "$DOS_N_FAKE_COMMANDS" "$DOS_MALICIOUS_COMMAND" "$DOS_SLEEP_DURATION_SEC"
	docker run -d --rm --name dos \
		--cpus "$DOS_CPU_LIMIT" \
		-e DOS_DURATION_SEC="$DOS_DURATION_SEC" \
		-e DOS_CMD="$DOS_CMD" \
		-e DOS_N_FAKE_COMMANDS="$DOS_N_FAKE_COMMANDS" \
		-e DOS_MALICIOUS_COMMAND="$DOS_MALICIOUS_COMMAND" \
		-e DOS_SLEEP_DURATION_SEC="$DOS_SLEEP_DURATION_SEC" dos

	sleep $DOS_DURATION_SEC

	docker kill dos 2>/dev/null || :
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

	teardown
	start_prometheus
	tracee_is_running || start_tracee

	run_dos

	wait_tracee_sink

	if [ "$TRACEE_BENCHMARK_OUTPUT_FILE" != "" ]; then
		benchmark_dir=${TRACEE_BENCHMARK_OUTPUT_FILE%/*}
		sudo rm -r "$benchmark_dir" 2>/dev/null || :
		mkdir -p "$benchmark_dir"
		run_benchmark >"$TRACEE_BENCHMARK_OUTPUT_FILE"
	else
		run_benchmark
	fi

	# [[ $call_teardown -eq 1 ]] && teardown
}

_main
