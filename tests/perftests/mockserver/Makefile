
all:
		run

build:
	docker build -t tracee-mockserver .

run:
		(docker ps | grep mockserv) || \
		docker run --rm -d --name tracee-mockserver -p 3434:3434 tracee-mockserver
