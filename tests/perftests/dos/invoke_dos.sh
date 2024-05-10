#!/bin/bash

# if [ "$#" -lt 3 ]; then
#   echo Usage: invoke_dos.sh [DOS_APP] [N_FAKE_COMMANDS] [REAL_COMMAND]
# #   DOS_CMD="/app/dos 4500 'echo kek > some_file && date && echo kek'"
# # else
#   # DOS_CMD="$@"
#   # DOS_CMD=$1
# fi

# while true; /app/dos 9000 'echo kek > some_file && date && echo kek'; done

# echo first: "$1"
# echo second

# while ((opt = getopt(argc, argv, "t:s:n:r:")) != -1) {
#     switch (opt) {
#         case 't':
#             timeout = atoi(optarg);
#             break;
#         case 's':
#             sleep_seconds = atof(optarg);
#             break;
#         case 'n':
#             n_fake_commands = atoi(optarg);
#             break;
#         case 'r':
#             real_command = optarg;
#             break;

DOS_APP=${DOS_APP:-/app/dos}
N_FAKE_COMMANDS=${N_FAKE_COMMANDS:-1000}
REAL_COMMAND=${REAL_COMMAND:-'echo kek > /tmp/some_file && date && echo kek'}
SLEEP_DURATION=${SLEEP_DURATION:-0.005}

# $DOS_APP -t $DOS_CMD -s $SLEEP_DURATION -r "$REAL_COMMAND" -n $N_FAKE_COMMANDS

while true; do
	$DOS_APP $N_FAKE_COMMANDS "$REAL_COMMAND"
	sleep $SLEEP_DURATION
done
