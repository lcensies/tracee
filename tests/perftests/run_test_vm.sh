#!/bin/bash -ex

# 1. Build tracee
# 2. Create snapshot
# 3. Invoke DoS
# 4. Gather metrics
# 5. Revert snapshot
BUILD_TRACEE=false
TRACEE_ROOT=$(git rev-parse --show-toplevel)

# VAGRANT_CMD="cd $TRACEE_ROOT && vagrant "

# TODO: discover forwarded port and auto choose it for SSH_CMD
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
echo "TRACEE_ROOT: $TRACEE_ROOT"

cd "$TRACEE_ROOT" && vagrant reload

$BUILD_TRACEE && $VM_SSH_CMD make -f builder/Makefile.tracee-container build-tracee

# $VM_SSH_CMD docker image ls | grep dos ||
# Build DoS container
$VM_SSH_CMD make -f builder/Makefile.dos-container

# Build tracee if necesarry
# $VM_SSH_CMD make -f builder/Makefile.tracee-container build-tracee

# Invoke test
$VM_SSH_CMD tests/perftests/dos_test.sh

echo VM_SSH_ROOT: $VM_SSH_ROOT
echo TRACEE_BENCHMARK_OUTPUT_FILE: "$TRACEE_BENCHMARK_OUTPUT_FILE"

$VM_SCP_CMD "$VM_SSH_ROOT:$TRACEE_BENCHMARK_OUTPUT_FILE" "$TRACEE_BENCHMARK_OUTPUT_FILE"

cat "$TRACEE_BENCHMARK_OUTPUT_FILE"

# TODO: create snapshot only if it doesn't exist
# $VAGRANT_CMD snapshot save tracee_vm base
# TODO: use CMD_VAGRANT
# cd "$TRACEE_ROOT" && vagrant snapshot restore "$VM_NAME" base
