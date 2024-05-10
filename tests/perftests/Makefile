SHELL := /bin/bash

include .env
# export


all: run-tracee

.PHONY: run-tracee
run-tracee:
	"${TRACEE_CMD}" "${TRACEE_FLAGS}"

.PHONY:
# TODO: parametrize mockserv port
run-mockserv:
	(docker ps | grep mockserv) || \
		docker run --rm -d --name tracee-mockserver -p 3434:3434 tracee-mockserver
