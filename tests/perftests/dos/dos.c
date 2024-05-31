#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>
#include <string.h>
#include <signal.h>

void run_mask_command(int n_iters)
{
    FILE *fp;

    for (int i = 0; i < n_iters; i++) {
        fp = fopen("/etc/passwd", "r");
        fclose(fp);
    }
}

struct timespec seconds_to_timespec(float sec)
{
    struct timespec req;

    req.tv_sec = (time_t) sec;
    req.tv_nsec = (long) ((sec - req.tv_sec) * 1e9);

    return req;
}

void update_counter(FILE *fd, int *command_counter)
{
    *command_counter = *command_counter + 1;

    ftruncate(fileno(fd), 0);
    rewind(fd);
    fprintf(fd, "%d", *command_counter);
}

void start_dos(int n_fake_syscalls, const char *real_command, float sleep_interval_sec)
{
    FILE *fpp;
    FILE *counter_fp;
    char buf[1024];
    int command_counter;

    struct timespec sleep_timespec = seconds_to_timespec(sleep_interval_sec);
    counter_fp = fopen("/tmp/dos/counter", "w+");
    command_counter = 0;

    while (1) {
        run_mask_command(n_fake_syscalls);

        // TODO: run malicious command only if some timestamp
        // is passed
        if ((fpp = popen(real_command, "r")) == NULL) {
            printf("Error opening pipe!\n");
            return;
        }

        while (fgets(buf, 1024, fpp) != NULL)
            printf("%s", buf);

        if (pclose(fpp)) {
            printf("Command not found or exited with error status\n");
            return;
        }

        update_counter(counter_fp, &command_counter);

        run_mask_command(n_fake_syscalls);

        nanosleep(&sleep_timespec, NULL);
    }
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

int main(int argc, char *argv[])
{
    char *real_command;
    int iters;
    float dos_timeout;
    float sleep_timeout;

    iters = atoi(getenv("DOS_N_FAKE_COMMANDS"));
    real_command = getenv("DOS_MALICIOUS_COMMAND");
    sleep_timeout = atof(getenv("DOS_SLEEP_DURATION_SEC"));
    dos_timeout = atof(getenv("DOS_DURATION_SEC"));

    setup_timeout(dos_timeout);
    printf("Running dos with %d iterations, %f sleep timeout, %s hidden command\n",
           iters,
           sleep_timeout,
           real_command);

    start_dos(iters, real_command, sleep_timeout);
}
