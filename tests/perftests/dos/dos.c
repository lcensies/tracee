#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>
#include <string.h>


void run_mask_command(int n_iters) {
  FILE *fp;

  // mask the real call
  for (int i = 0; i < n_iters; i++) {
    fp = fopen("/etc/passwd", "r");
    fclose(fp);
  }
}

struct timespec seconds_to_timespec(float sec) {
    struct timespec req;

    req.tv_sec = (time_t)sec; // Extract seconds
    req.tv_nsec = (long)((sec - req.tv_sec) * 1e9); // Extract nanoseconds

    return req;
}

void start_dos(int n_fake_syscalls, const char *real_command, float sleep_interval_sec) {

  FILE *fpp;
  char buf[1024];
  struct timespec sleep_timespec = seconds_to_timespec(sleep_interval_sec);

  while (1) {

    run_mask_command(n_fake_syscalls);

    //-----------------Real call--------------------//

    if ((fpp = popen(real_command, "r")) == NULL) {
      printf("Error opening pipe!\n");
      return;
    }

    while (fgets(buf, 1024, fpp) != NULL)
      printf("OUTPUT: %s", buf);

    if (pclose(fpp)) {
      printf("Command not found or exited with error status\n");
      return;
    }

    run_mask_command(n_fake_syscalls);

    nanosleep(&sleep_timespec, NULL);
  }
}

void print_usage() {
  printf("Usage: dos [N_FAKE_SYSCALLS] [REAL_CALL] [SLEEP_TIMEOUT]");
}

int main(int argc, char *argv[])
{
  char* real_command;
  int iters;
  float sleep_timeout;

  printf("Argc: %d\n", argc);
  if (argc != 4){
    print_usage();
    return EXIT_FAILURE;
  }

  iters = atoi(argv[1]);
  real_command = argv[2];
  sleep_timeout = atof(argv[3]);

  start_dos(iters, real_command, sleep_timeout);

}


