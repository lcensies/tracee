#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <wait.h>

void run_mask_command(int n_iters) {
  FILE *fp;

  // mask the real call
  for (int i = 0; i < n_iters; i++) {
    fp = fopen("/etc/passwd", "r");
    fclose(fp);
  }
}

void start_dos(int n_fake_syscalls, const char *real_command) {

  FILE *fpp;
  char buf[1024];

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
}

// It seems liks fork_dos doesn't generate enough events. 
int main(int argc, char *argv[]) {
  int iters;
  int n_processes;
  char *real_command;
  int pid;

  if (argc != 4) {
    printf("Usage: forkdos [number of processes] [number of dummy syscalls] "
           "[real command]!\n");
    return 0;
  }

  n_processes = atoi(argv[1]);
  iters = atoi(argv[2]);
  real_command = argv[3];

  for (int i = 0; i < n_processes; i++) {
    switch (pid = fork()) {
    case -1:
      perror("fork");
      exit(EXIT_FAILURE);
    case 0:
      start_dos(iters, real_command);
      exit(EXIT_SUCCESS);
    }
  }

  while (wait(NULL) > 0)
    ;
}
