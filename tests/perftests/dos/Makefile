.PHONY: all
all:
	$(MAKE) build

#
# make
#

.ONESHELL:
SHELL = /bin/sh

MAKE = make -f $(shell find . -name Makefile.dos-container)
MAKEFLAGS += --no-print-directory
MAKE_DIR := $(dir $(abspath $(firstword $(MAKEFILE_LIST))))

#
# tools
#

CMD_DOCKER ?= docker
CMD_DOCKER_COMPOSE ?= docker-compose
DOS_CONT_DOCKERFILE = ${MAKE_DIR}/Dockerfile
DOS_CONT_NAME=dos:latest

#
# config
#

DOS_CPU_LIMIT ?= 0.8
DOS_SLEEP_DURATION_SEC ?= 0
DOS_DURATION_SEC ?= 60
DOS_CMD ?= /app/dos
DOS_N_FAKE_COMMANDS ?= 20000
DOS_MALICIOUS_COMMAND ?= cat /proc/sys/kernel/randomize_va_space

.PHONY: build
build:
	${CMD_DOCKER} build \
		-f ${DOS_CONT_DOCKERFILE} \
		-t ${DOS_CONT_NAME} \
		${MAKE_DIR}


	# --cpus "${DOS_CPU_LIMIT}" 
run: build
	# ${CMD_DOCKER_COMPOSE} up -d
		${CMD_DOCKER} run -d --rm --name dos \
		-v /tmp/dos:/tmp/dos \
		-e DOS_DURATION_SEC="${DOS_DURATION_SEC}" \
		-e DOS_CMD="${DOS_CMD}" \
		-e DOS_N_FAKE_COMMANDS="${DOS_N_FAKE_COMMANDS}" \
		-e DOS_MALICIOUS_COMMAND="${DOS_MALICIOUS_COMMAND}" \
		-e DOS_SLEEP_DURATION_SEC="${DOS_SLEEP_DURATION_SEC}" ${DOS_CONT_NAME}
