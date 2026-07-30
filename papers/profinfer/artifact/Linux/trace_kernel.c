#include <uapi/linux/ptrace.h>
#include <linux/blkdev.h>
#include <linux/sched.h>

BPF_HASH(pid_store);
BPF_PERF_OUTPUT(eventsKernel);

struct data_t {
    u32 type;
    u64 timestamp;
    char prev_comm[16];
    u32 prev_pid;
    u32 prev_ppid;
    u32 prev_prio;
    u32 prev_state;

    char next_comm[16];
    u32 next_pid;
    u32 next_ppid;
    u32 next_prio;    
};


struct sched_wakeup_args_t{
  u16 common_type;
  char commpn_flags;
  char common_preempt_count;
  u32 common_pid;
  char prev_comm[16];
  u32 pid;
  u32 prio;
  u32 success;
  u32 target_cpu;
};


int get_sched_wakeup_events(struct sched_wakeup_args_t *ctx) {
  bpf_trace_printk("Sched_switch");
  u32 filter = 1;
  struct data_t data = {};
  data.timestamp = bpf_ktime_get_ns();
  data.type = 0;
  //bpf_probe_read_kernel(&data.next_pid, sizeof(data.next_pid), &PT_REGS_PARM1(ctx)+4);
  data.next_pid = ctx->pid;
  bpf_probe_read_kernel(&data.prev_comm, sizeof(data.prev_comm), ctx->prev_comm);

  //data.prev_comm = ctx->prev_comm;
  u64 pid = (u64) (data.next_pid); 
  //bpf_get_current_pid_tgid();
  if(pid != 0)
  {
    if(pid_store.lookup(&pid) != NULL || filter == 0)
    {
      eventsKernel.perf_submit(ctx, &data, sizeof(data));
    }  
  }
  return 0;
}

int get_sched_switch_events(struct pt_regs *ctx,  struct task_struct *prev) {
 bpf_trace_printk("Sched_switch"); 
  u32 filter = 1;
  struct data_t data = {};
  data.timestamp = bpf_ktime_get_ns();
  struct task_struct *curr = (struct task_struct *)bpf_get_current_task();
  u64 pid1 = (u64)(curr->pid);
  u64 pid2 = (u64)(prev->pid);
  if(pid_store.lookup(&pid1) != NULL || pid_store.lookup(&pid2) != NULL || filter == 0)
  {
    data.type = 1;
    bpf_probe_read_kernel(&data.prev_comm, sizeof(data.prev_comm), prev->comm);
    data.prev_pid = prev->pid;
    data.prev_ppid = prev->real_parent->pid;
    data.prev_prio = prev->prio;
    data.prev_state = prev->__state;

    bpf_get_current_comm(&(data.next_comm),16);
    data.next_pid = curr->pid;
    data.next_ppid = curr->real_parent->pid;
    data.next_prio = curr->prio;
    
    eventsKernel.perf_submit(ctx, &data, sizeof(data));
  }

  return 0;
}

struct sched_switch_args_t{
  u16 common_type;
  char commpn_flags;
  char common_preempt_count;
  u32 common_pid;
  
  char prev_comm[16];
  u32 prev_pid;
  u32 prev_prio;
  u64 prev_state;

  char next_comm[16];
  u32 next_pid;
  u32 next_prio;
};

int get_sched_switch_tp_events(struct sched_switch_args_t *ctx) {
  bpf_trace_printk("Sched_switch"); 
  u32 filter = 1;
  struct data_t data = {};
  data.timestamp = bpf_ktime_get_ns();
  u64 pid1 = (u64)(ctx->prev_pid);
  u64 pid2 = (u64)(ctx->next_pid);
  if(pid_store.lookup(&pid1) != NULL || pid_store.lookup(&pid2) != NULL || filter == 0)
  {
    data.type = 2;
    bpf_probe_read_kernel(&data.prev_comm, sizeof(data.prev_comm), ctx->prev_comm);
    data.prev_pid = ctx->prev_pid;
    //data.prev_ppid = prev->real_parent->pid;
    data.prev_prio = ctx->prev_prio;
    data.prev_state = ctx->prev_state;

    bpf_probe_read_kernel(&data.next_comm, sizeof(data.prev_comm), ctx->next_comm);
    data.next_pid = ctx->next_pid;
    //data.prev_ppid = prev->real_parent->pid;
    data.next_prio = ctx->next_prio;
    
    eventsKernel.perf_submit(ctx, &data, sizeof(data));
  }

  return 0;
}

/***********
 * For mmap: /sys/kernel/tracing/events/syscalls/sys_enter_mmap/format
 * name: sys_enter_mmap
ID: 30
format:
        field:unsigned short common_type;       offset:0;       size:2; signed:0;
        field:unsigned char common_flags;       offset:2;       size:1; signed:0;
        field:unsigned char common_preempt_count;       offset:3;       size:1; signed:0;
        field:int common_pid;   offset:4;       size:4; signed:1;

        field:int __syscall_nr; offset:8;       size:4; signed:1;
        field:unsigned long addr;       offset:16;      size:8; signed:0;
        field:unsigned long len;        offset:24;      size:8; signed:0;
        field:unsigned long prot;       offset:32;      size:8; signed:0;
        field:unsigned long flags;      offset:40;      size:8; signed:0;
        field:unsigned long fd; offset:48;      size:8; signed:0;
        field:unsigned long off;        offset:56;      size:8; signed:0;

print fmt: "addr: 0x%08lx, len: 0x%08lx, prot: 0x%08lx, flags: 0x%08lx, fd: 0x%08lx, off: 0x%08lx", ((unsigned long)(REC->addr)), ((unsigned long)(REC->len)), ((unsigned long)(REC->prot)), ((unsigned long)(REC->flags)), ((unsigned long)(REC->fd)), ((unsigned long)(REC->off))
 */

