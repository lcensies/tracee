#include <stdio.h>
#include <errno.h>
#include <stdlib.h>
#include <signal.h>
#include <unistd.h>
#include <error.h>
#include <string.h>
#include <time.h>
#include <argp.h>

// Function Prototypes
void perform_fake_commands(int n_fake_commands);
void execute_real_command(char *command);
void high_precision_sleep(struct timespec duration);
struct timespec seconds_to_timespec(float sec);
void setup_timeout(int timeout);
void timeout_handler(int sig);

void run_dos(int n_fake_commands, char *real_command, float sleep_seconds);

const char *argp_program_version = "example 1.0";
const char *argp_program_bug_address = "<bug-report-email@example.com>";
static char doc[] = "A minimal Argp example.";
static char args_doc[] = "ARG1 ARG2";

static struct argp_option options[] = {
    {"timeout", 't', 0, 0, "Duration of the DoS"},
    {"n_fake_commands", 'n', 0, 0, "Number of fake commands to execute"},
    {"sleep", 's', 0, 0, "Sleep duration in seconds between execution rounds"},
    {"real_command", 'r', 0, 0, "Masqueraded real command executed once in round"},
    {"quiet", 'q', 0, OPTION_ALIAS},
    {0}};

struct arguments {
    int timeout;
    int n_fake_commands;
    float sleep_seconds;
    char *real_command;
    int quiet;
};

static error_t parse_opt(int key, char *arg, struct argp_state *state)
{
    struct arguments *arguments = state->input;

    switch (key) {
        case 'q':
            arguments->quiet = 1;
            break;
        case 't':
            arguments->timeout = atoi(arg);
            break;
        case 'n':
            arguments->n_fake_commands = atoi(arg);
            break;
        case 'r':
            arguments->real_command = strdup(arg);
            break;
        case 's':
            arguments->sleep_seconds = atof(arg);
            break;
        default:
            return ARGP_ERR_UNKNOWN;
    }
    return 0;
}

static struct argp argp = {options, parse_opt, args_doc, doc};

void run_dos(int n_fake_commands, char *real_command, float sleep_seconds)
{
    struct timespec sleep_ts = seconds_to_timespec(sleep_seconds);

    if (n_fake_commands <= 0) {
        fprintf(stderr, "Number of fake commands is not provided");
        exit(EXIT_FAILURE);
    }
    if (real_command == NULL) {
        fprintf(stderr, "Real command is not provided");
        exit(EXIT_FAILURE);
    }

    printf("N_FAKE_COMMANDS: %d\n", n_fake_commands);
    printf("SLEEP_DURATION: %f\n", sleep_seconds);
    printf("REAL_COMMAND: %s", real_command);

    while (1) {
        // Perform DOS simulation
        perform_fake_commands(n_fake_commands / 2);
        execute_real_command(real_command);
        perform_fake_commands(n_fake_commands / 2);

        nanosleep(&sleep_ts, NULL);
    }
}

struct timespec seconds_to_timespec(float sec)
{
    struct timespec req;

    req.tv_sec = (time_t) sec;                       // Extract seconds
    req.tv_nsec = (long) ((sec - req.tv_sec) * 1e9); // Extract nanoseconds

    return req;
}

void timeout_handler(int sig)
{
    printf("DoS is timed out\n");
    exit(EXIT_SUCCESS);
}

void setup_timeout(int timeout)
{
    signal(SIGALRM, timeout_handler);
    alarm(timeout);
}

void perform_fake_commands(int n_fake_commands)
{
    for (int i = 0; i < n_fake_commands; i++) {
        FILE *fp = fopen("/etc/passwd", "r");
        fclose(fp);
    }
}

void execute_real_command(char *command)
{
    size_t buf_size = 1024 * 50;
    char buf[buf_size];
    FILE *fpp;

    if ((fpp = popen(command, "r")) == NULL) {
        fprintf(stderr, "Error opening pipe!\n");
        exit(-1);
    }

    while (fgets(buf, buf_size, fpp) != NULL) {
        printf("OUTPUT: %s", buf);
    }

    if (pclose(fpp)) {
        fprintf(stderr, "Command not found or exited with error status\n");
        exit(-1);
    }
}

int main(int argc, char *argv[])
{
    struct arguments arguments;

    // Default values.
    arguments.quiet = 0;
    arguments.n_fake_commands = 1000;
    arguments.real_command = "echo kek > /tmp/some_file && date && echo kek";
    arguments.timeout = 60;
    arguments.sleep_seconds = 0.005;

    argp_parse(&argp, argc, argv, 0, 0, &arguments);

    if (arguments.timeout > 0) {
        setup_timeout(arguments.timeout);
    }

    printf("DoS app: %s\n", argv[0]);
    printf("Timeout: %d seconds\n", arguments.timeout);

    run_dos(arguments.n_fake_commands, arguments.real_command, arguments.sleep_seconds);

    return 0;
}
