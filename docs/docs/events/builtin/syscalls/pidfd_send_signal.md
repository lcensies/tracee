
# pidfd_send_signal

## Intro
The event `pidfd_send_signal` allows to send a signal to a specific process specified by a PID file descriptor, rather than its 'traditional' process ID. 

## Description
The `pidfd_send_signal()` syscall invokes `SIGSYS` on the process specified by the `pidfd` argument, and optionally with additional information from the `info`. Unlike the `kill()` syscall, this syscall can express the relative process hierarchy by passing the PID file descriptor instead of the real PID.

The extra flags currently supported are `PIDFD_SEND_SIGCONT` and `PIDFD_SEND_SIGNAL_OWNER`, as specified in the `flags` argument. The former is used to inform the process waiting on a pidfd to continue its execution, while the latter is intended to allow a parent process to prevent other users on the same machine to interfere with the process group of the PID file descriptor.

This syscall may be useful when there is a need to perform complex operations on a process or process group from a parent process. It also prevents race conditions which could occur between a child process being created and the parent process being notified of it, since the parent process can simply keep the PID trigger in a file descriptor and perform the action when signalled.

## Arguments
* `pidfd`:`int` - the file descriptor of a file with a process ID indicating the specific process the signal will be sent to.
* `sig`:`int` - the signal that will be sent to the process.
* `info`:`siginfo_t*`[U] - Optional additional data, such as the pid of the process that sent the signal and the real uid, which is used to verify the sender's privileges.
* `flags`:`unsigned int` - Set of flags which might change the behaviour of the syscall.

### Available Tags
* U - Originated from user space (for example, pointer to user space memory used to get it).

## Hooks
### send_signal
#### Type 
Kprobes + Uprobes
#### Purpose 
To handle the sending of signals.

## Example Use Case
The `pidfd_send_signal` syscall can be used for process synchronization techniques, where a parent process can wait on a PID file descriptor to be signalled before being notified of the completion of a child process.

This idea was inspired in part by `ptrace(2)`, which can be used to place a trace on a process group in order to observe its execution. However, `ptrace` also provides a means of signalling and process suspension features which are not necessary or desirable in certain types of applications.

## Issues
The implementation of this syscall currently has a bug which can cause some signals to be lost when sent to processes whose parent process is waiting for them.

## Related Events
* `kill()` - sends the signal specified by `sig` to the process specified by `pid`
* `getpid()` - returns the process ID of the calling process.
* `waitpid()` - suspends execution of the calling process until a child specified by `pid` terminates. 
* `ptrace()` - trace processes. It can be used to intercept, observe and manipulate the execution of process and its children.

> This document was automatically generated by OpenAI and needs review. It might
> not be accurate and might contain errors. The authors of Tracee recommend that
> the user reads the "events.go" source file to understand the events and their
> arguments better.