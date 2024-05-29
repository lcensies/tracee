#!/bin/bash -x

TRACEE_ROOT=$(git rev-parse --show-toplevel)
SCRIPT_DIR="$(cd ${0%/*} && pwd -P)"
source "$SCRIPT_DIR/.env"

# TODO: auto discover forwarded port and auto choose it for SSH_CMD
# default: 22 (guest) => 2222 (host) (adapter 1)
VM_PORT=2222
VM_SSH_PRIVKEY="$TRACEE_ROOT/.vagrant/machines/default/virtualbox/private_key"

VM_SSH_ROOT="vagrant@127.0.0.1"
VM_SSH_OPTS="-i $VM_SSH_PRIVKEY -p $VM_PORT -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
VM_SCP_CMD="scp -i $VM_SSH_PRIVKEY -P $VM_PORT -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
# cd to tracee root directory inside VM by default
# pass environmental variables that are starting from TRACEE or DOS prefix to remote host
# for example, TRACEE_BENCHMARK_OUTPUT_FILE
VM_SSH_CMD="ssh $VM_SSH_OPTS $VM_SSH_ROOT cd /vagrant && source ~/.profile && $(env | sed 's/;/\;/g' | grep -E 'TRACEE|DOS')"

[[ -f "$VM_SSH_PRIVKEY" ]] || (echo "ssh private key is not found at $VM_SSH_PRIVKEY" && exit 1)

# start mock server to receive events
cd ${SCRIPT_DIR} && make run-mockserv
# ensure tracee dir exists on host
mkdir -p /tmp/tracee

cd "$TRACEE_ROOT"

run_test() {
	$VM_RELOAD_NEEDED && vagrant reload

	$BUILD_TRACEE && $VM_SSH_CMD make -f builder/Makefile.tracee-container build-tracee

	# Invoke test
	# TODO: auto exit
	$VM_SSH_CMD "tests/perftests/dos_test.sh && exit"

	# Fetch results back to host
	$VM_SSH_CMD sudo chown -R vagrant:vagrant /tmp/tracee
	$VM_SCP_CMD -r "$VM_SSH_ROOT:/tmp/tracee" /tmp
}

# echo reports dir: $PERFTEST_REPORTS_DIR && exit 1

if [ "$TEST_N_RUNS" -gt 1 ]; then
	for i in $(seq 1 $TEST_N_RUNS); do
		run_test
		mkdir -p "$PERFTEST_REPORTS_DIR/$i"
		cp -r /tmp/tracee/ "$PERFTEST_REPORTS_DIR/$i"
		# Save current config environment to reference it later
		cp "$SCRIPT_DIR/.env" "$PERFTEST_REPORTS_DIR/$i"
	done
else
	run_test
	mkdir -p "$PERFTEST_REPORTS_DIR/"
	cp -r /tmp/tracee/ "$PERFTEST_REPORTS_DIR/"
	cp "$SCRIPT_DIR/.env" "$PERFTEST_REPORTS_DIR/"
fi

# TODO: create snapshot only if it doesn't exist
# $VAGRANT_CMD snapshot save tracee_vm base
# cd "$TRACEE_ROOT" && vagrant snapshot restore "$VM_NAME" base

python3 "${SCRIPT_DIR}/analyze_ev.py"
python3 "${SCRIPT_DIR}/get_top_io.py"
