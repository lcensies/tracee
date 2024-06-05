
SHELL := /bin/bash

all: dos_test

.PHONY: dos_test
dos_test:
	./run_test_vm.sh

.PHONY: run_dos
run_dos:
	./dos_test.sh run_dos

.PHONY: run-tracee
run-tracee:
	./dos_test.sh stop_tracee
	./dos_test.sh run_tracee

.PHONY: stop-tracee
stop-tracee:
	./dos_test.sh stop_tracee

.PHONY:
# TODO: parametrize mockserv port
run-mockserv:
	make -f mockserver/Makefile run
	
