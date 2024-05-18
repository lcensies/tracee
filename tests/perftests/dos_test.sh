#!/bin/bash -ex

SCRIPT_DIR="$(cd ${0%/*} && pwd -P)"
source "$SCRIPT_DIR/.env"

run_prometheus() {
	perf_compose="$TRACEE_ROOT/performance/dashboard/docker-compose.yml"
	docker-compose -f "$perf_compose" up -d
}

clear_prometheus() {

	perf_compose=$TRACEE_ROOT/performance/dashboard/docker-compose.yml
	docker-compose -f $perf_compose down
	docker volume rm dashboard_prometheus_data 2>/dev/null || :

	# Set the match[] argument to "{}" to match all metrics
	# MATCHERS='{}'
	# curl -X POST "$PROMETHEUS_ADDR/api/v1/admin/tsdb/delete_series" -H "Content-Type: application/json" --data "{\"match[]\":[\"$MATCHERS\"]}"

}

clear_server() {
	timeout 1 curl -X POST "$WEBHOOK_ADDR/reset" 2>/dev/null || :
}

stop_postgres() {
	docker-compose -f "$PGBENCH_ROOT/docker-compose.yml" down
}

tracee_is_running() {
	if [ -n "$(docker ps -q --filter "ancestor=tracee")" ]; then
		echo true
	else
		echo false
	fi
}

# TODO: switch on workload type
stop_workloads() {
	stop_postgres
	docker stop dos 2>/dev/null || :
}

# Teardown outdated instances of dos and tracee containers
teardown() {
	echo Tearing down existing tracee and dos containers

	stop_workloads
	stop_tracee

	clear_prometheus
	clear_server
}

build_tracee_docker() {
	(docker image ls | grep $DOCKER_TRACEE_IMAGE) ||
		(cd /vagrant && make -f builder/Makefile.tracee-container build-tracee)
}

run_tracee() {
	echo Starting tracee

	if [ "${TRACEE_NO_CONTAINER}" = true ]; then
		TRACEE_CMD="/vagrant/dist/tracee"
		sudo -b $TRACEE_CMD $TRACEE_FLAGS
	else
		# build_tracee_docker
		TRACEE_CMD="docker run --cpus ${TRACEE_CPU_LIMIT} --name tracee -e TRACEE_EXE=${TRACEE_EXE} ${DOCKER_INTERACTIVE_FLAG} --rm --pid=host --cgroupns=host --privileged -v /etc/os-release:/etc/os-release-host:ro -v /boot:/boot -v /var/run:/var/run:ro -v /tmp/tracee:/tmp/tracee -v ${SCRIPT_DIR}/tracee:/etc/tracee -p 3366:3366 $DOCKER_TRACEE_IMAGE"
		$TRACEE_CMD $TRACEE_FLAGS
	fi

	echo TRACEE_CMD is "$TRACEE_CMD"

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

run_pgbench() {
	exported_env="$(cat "$SCRIPT_DIR/.env" | grep -E "^PG|^DATABASE|DOCKER_POSTGRES" | grep -v exported)"
	echo "$exported_env" >"$PGBENCH_ROOT/.env"
	cd "$PGBENCH_ROOT" && source "$PGBENCH_ROOT/.env" && make db && make pgbench
}

run_dos() {

	cd /vagrant && make -f builder/Makefile.dos-container

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

}

# TODO: switch to Makefile
run_workload() {
	case "$TEST_TYPE" in
	"pgbench") run_pgbench ;;
	"dos") run_dos ;;
	"sleep") sleep $TEST_DURATION ;;
	*) echo invalid test type && exit 1 ;;
	esac
}

# Wait until all events from cache are consumed
wait_tracee_sink() {
	cache_load=1

	while [ "$cache_load" != "0" ]; do
		cache_load="$(curl -g "$PROMETHEUS_ADDR/api/v1/query?query=tracee_ebpf_cache_load" | jq ".data.result" | jq -c " .[].value | .[1]")"
		# cache_load="$(${TRACEE_BENCH_CMD} 2>/dev/null | jq .cacheLoad)"
		echo "cache load: $cache_load"
		sleep 1
		if [ "$(tracee_is_running)" = "false" ]; then
			echo "tracee is stopped; returning immediately"
			return
		fi
	done
}

run_benchmark() {
	echo -e "\n"

	if [ "$TRACEE_BENCHMARK_OUTPUT_FILE" != "" ]; then
		benchmark_dir=${TRACEE_BENCHMARK_OUTPUT_FILE%/*}
		sudo rm -r "$benchmark_dir" 2>/dev/null || :
		mkdir -p "$benchmark_dir"
		$TRACEE_BENCH_CMD >"$TRACEE_BENCHMARK_OUTPUT_FILE" 2>/dev/null
	else
		$TRACEE_BENCH_CMD 2>/dev/null
	fi
}

fetch_events_stats() {
	curl "$WEBHOOK_ADDR" | sudo tee "$EVENTS_STATS_FILE"
	curl "$WEBHOOK_ADDR/fileevents" | sudo tee "$FILE_IO_STATS_FILE"
	# curl -g "$PROMETHEUS_ADDR/api/v1/query?query=tracee_ebpf_lostevents_total[120m]" | sudo tee "$EVENTS_LOST_STATS_FILE"

}

fetch_post_sleep_stats() {
	curl -g "$PROMETHEUS_ADDR/api/v1/query?query=process_resident_memory_bytes[120m]&job=tracee" | sudo tee "$TRACEE_MEMORY_STATS_FILE"
	curl -g "$PROMETHEUS_ADDR/api/v1/query?query=tracee_ebpf_cache_load[120m]" | sudo tee "$CACHE_LOAD_STATS_FILE"
	curl -g "$PROMETHEUS_ADDR/api/v1/query?query=tracee_ebpf_events_cached[120m]" | sudo tee "$EVENTS_CACHED_STATS_FILE"
	curl -g "$PROMETHEUS_ADDR/api/v1/query?query=tracee_ebpf_events_total[120m]" | sudo tee "$EVENTS_RATE_STATS_FILE"
	curl -g "$PROMETHEUS_ADDR/api/v1/query?query=tracee_ebpf_lostevents_total[120m]" | sudo tee "$EVENTS_LOST_STATS_FILE"
}

# TODO: refactor
stop_tracee() {
	# sudo killall tracee 2>/dev/null || :
	docker stop tracee 2>/dev/null || :

	while [ "$(tracee_is_running)" = "true" ]; do
		sleep 0.1
	done
}

set_webhook_ts_limit() {
	echo Setting events receiving timestamp limit to $(date)
	curl -d "{\"timestamp\":$EPOCHSECONDS}" -H "Content-Type: application/json" -X POST $WEBHOOK_ADDR
}

_main() {

	teardown

	run_prometheus
	run_tracee
	run_workload

	set_webhook_ts_limit
	stop_workloads
	# wait_tracee_sink

	fetch_events_stats
	sleep $POST_TEST_SLEEP_SEC
	fetch_post_sleep_stats
}

_main
