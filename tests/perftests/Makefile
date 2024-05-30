
SHELL := /bin/bash

all: run-tracee

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
	docker build -t tracee-mockserver mockserver
	(docker ps | grep mockserv) || \
		docker run --rm -d --name tracee-mockserver -p 3434:3434 tracee-mockserver
	
