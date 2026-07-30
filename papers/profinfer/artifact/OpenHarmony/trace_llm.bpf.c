// llama_uprobe.bpf.c
// Build: clang -O2 -g -target bpf -c llama_uprobe.bpf.c -o llama_uprobe.bpf.o
#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_tracing.h>
#include <bpf/bpf_core_read.h>
#include "trace_llm.h"

char LICENSE[] SEC("license") = "GPL";
const __u32 VERSION SEC("version") = 1;

#define OFFSET_NE 16
#define OFFSET_NB 48
#define OFFSET_OP 80
#define OFFSET_SRC 152
#define OFFSET_VIEW_SRC 232
#define OFFSET_VIEW_OFFS 240
#define OFFSET_DATA 248
#define OFFSET_NAME 256

#define MAX_NUM_EXPERTS 4
#define MAX_NUM_OPS 128

#define OFFSET_N_THREADS 16 // 4 bytes int to read
#define OFFSET_THREADPOOL 24 // 8 bytes ggml_threadpool pointer 

#ifdef DIMS
// Needs to be adapted if ggml change op enum
#define ID_MUL_MAT_ID 28
#endif

// Track which ops are activated
struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, MAX_NUM_OPS);
    __type(key, __u32);
    __type(value, __u8);
} activated_ops SEC(".maps");

// Track per-process tracing status
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 10240);
    __type(key, __u32); // pid -> key
    __type(value, __u8);
} op_tracing_on SEC(".maps");

// Replace ring buffer with perf event array
struct {
    __uint(type, BPF_MAP_TYPE_PERF_EVENT_ARRAY);
    __uint(max_entries, 0);
    __type(key, int);
    __type(value, __u32);
} events SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 10240);
    __type(key, __u32);
    __type(value, __s32);
} pid_to_threads SEC(".maps");

// ----------------------------------------------------
// llama_decode start
// ----------------------------------------------------
SEC("uprobe")
int probe_llama_decode_start(struct pt_regs *ctx)
{
    struct data_t d = {};
    u64 ts = bpf_ktime_get_ns();
    u64 pid_tgid = bpf_get_current_pid_tgid();

    d.Ts = ts;
    d.pid = pid_tgid & 0xFFFFFFFF;
    d.tid = pid_tgid >> 32;
    d.cpu = bpf_get_smp_processor_id();
    d.type = 10;

    bpf_perf_event_output(ctx, &events, BPF_F_CURRENT_CPU, &d, sizeof(d));
    return 0;
}

// ----------------------------------------------------
// llama_decode end
// ----------------------------------------------------
SEC("uretprobe")
int probe_llama_decode_end(struct pt_regs *ctx)
{
    struct data_t d = {};
    u64 ts = bpf_ktime_get_ns();
    u64 pid_tgid = bpf_get_current_pid_tgid();

    d.Ts = ts;
    d.pid = pid_tgid & 0xFFFFFFFF;
    d.tid = pid_tgid >> 32;
    d.cpu = bpf_get_smp_processor_id();
    d.type = 15;

    bpf_perf_event_output(ctx, &events, BPF_F_CURRENT_CPU, &d, sizeof(d));
    return 0;
}

// ----------------------------------------------------
// ggml_compute_forward start
// ----------------------------------------------------
SEC("uprobe")
int probe_ggml_compute_forward_start(struct pt_regs *ctx)
{
    struct data_t d = {};
    u64 ts = bpf_ktime_get_ns();
    u64 pid_tgid = bpf_get_current_pid_tgid();

    d.Ts = ts;
    d.pid = pid_tgid & 0xFFFFFFFF;
    d.tid = pid_tgid >> 32;
    d.cpu = bpf_get_smp_processor_id();
    d.type = 20;

    void *void_ptr_reg_2 = (void *)PT_REGS_PARM2(ctx); // ggml_tensor* base pointer
    u16 op = 0;

    bpf_core_read_user(&op, sizeof(op), (void *)((char *)void_ptr_reg_2 + OFFSET_OP));
    d.op = op;

    // Read operator name string
    bpf_core_read_user_str(d.name, sizeof(d.name), (void *)((char *)void_ptr_reg_2 + OFFSET_NAME));

#ifdef DIMS
    // Tensor addresses
    u64 tensor_address, first_src_addr, second_src_addr;
    bpf_core_read_user(&tensor_address, sizeof(d.tensor_address), &PT_REGS_PARM2(ctx));
    bpf_core_read_user(&first_src_addr, sizeof(d.first_src_addr), (char *)void_ptr_reg_2 + OFFSET_SRC);
    bpf_core_read_user(&second_src_addr, sizeof(d.second_src_addr), (char *)void_ptr_reg_2 + OFFSET_SRC + 8);

    d.tensor_address = tensor_address;
    d.first_src_addr = first_src_addr;
    d.second_src_addr = second_src_addr;
    
    // if (d.op == ID_MUL_MAT_ID) {
    //     bpf_core_read_user(&third_src_addr, sizeof(d.third_src_addr), (char *)void_ptr_reg_2 + OFFSET_SRC + 16);
    //     d.third_src_addr = third_src_addr;
    // }

    // Read ne0..ne3
    bpf_core_read_user(&d.ne0, sizeof(d.ne0), (char *)void_ptr_reg_2 + OFFSET_NE);
    bpf_core_read_user(&d.ne1, sizeof(d.ne1), (char *)void_ptr_reg_2 + OFFSET_NE + 8);
    bpf_core_read_user(&d.ne2, sizeof(d.ne2), (char *)void_ptr_reg_2 + OFFSET_NE + 16);
    bpf_core_read_user(&d.ne3, sizeof(d.ne3), (char *)void_ptr_reg_2 + OFFSET_NE + 24);

    // Read src0_ne[4], src1_ne[4], src2_ne[4]
    for (int i = 0; i < 4; i++) {
        bpf_core_read_user(&d.src0_ne[i], sizeof(d.src0_ne[i]), (void *)((void *)first_src_addr + OFFSET_NE + i * 8));
        bpf_core_read_user(&d.src1_ne[i], sizeof(d.src1_ne[i]), (void *)((void *)second_src_addr + OFFSET_NE + i * 8));
        // if (d.op == ID_MUL_MAT_ID) {
        //     bpf_core_read_user(&d.src2_ne[i], sizeof(d.src2_ne[i]), (void *)((void *)third_src_addr + OFFSET_NE + i * 8));
        // }
    }
#endif // DIMS

    bpf_perf_event_output(ctx, &events, BPF_F_CURRENT_CPU, &d, sizeof(d));
    return 0;
}

// ----------------------------------------------------
// ggml_compute_forward end
// ----------------------------------------------------
SEC("uretprobe")
int probe_ggml_compute_forward_end(struct pt_regs *ctx)
{
    struct data_t d = {};
    u64 ts = bpf_ktime_get_ns();
    u64 pid_tgid = bpf_get_current_pid_tgid();

    d.Ts = ts;
    d.pid = pid_tgid & 0xFFFFFFFF;
    d.tid = pid_tgid >> 32;
    d.cpu = bpf_get_smp_processor_id();
    d.type = 25;

    bpf_perf_event_output(ctx, &events, BPF_F_CURRENT_CPU, &d, sizeof(d));
    return 0;
}

// ----------------------------------------------------
// ggml_backend_graph_compute_async start
// ----------------------------------------------------
SEC("uprobe")
int probe_ggml_backend_graph_compute_async_start(struct pt_regs *ctx)
{
    struct data_t d = {};
    u64 ts = bpf_ktime_get_ns();
    u64 pid_tgid = bpf_get_current_pid_tgid();

    d.Ts = ts;
    d.pid = pid_tgid & 0xFFFFFFFF;
    d.tid = pid_tgid >> 32;
    d.cpu = bpf_get_smp_processor_id();
    d.type = 30;

    u64 ggml_backend_addr = 0;
    bpf_core_read_user(&ggml_backend_addr, sizeof(u64 *), &PT_REGS_PARM1(ctx));
    bpf_core_read_user(&d.guid, sizeof(d.guid), (void *)ggml_backend_addr);

    bpf_perf_event_output(ctx, &events, BPF_F_CURRENT_CPU, &d, sizeof(d));
    return 0;
}

// ----------------------------------------------------
// ggml_backend_graph_compute_async end
// ----------------------------------------------------
SEC("uretprobe")
int probe_ggml_backend_graph_compute_async_end(struct pt_regs *ctx)
{
    struct data_t d = {};
    u64 ts = bpf_ktime_get_ns();
    u64 pid_tgid = bpf_get_current_pid_tgid();

    d.Ts = ts;
    d.pid = pid_tgid & 0xFFFFFFFF;
    d.tid = pid_tgid >> 32;
    d.cpu = bpf_get_smp_processor_id();
    d.type = 35;

    bpf_perf_event_output(ctx, &events, BPF_F_CURRENT_CPU, &d, sizeof(d));
    return 0;
}

SEC("uprobe")
int probe_ggml_graph_compute_start(struct pt_regs *ctx)
{
    struct data_t d = {};
    u64 ts = bpf_ktime_get_ns();
    u64 pid_tgid = bpf_get_current_pid_tgid();
    int ret = 0;

    d.Ts = ts;
    d.pid = pid_tgid & 0xFFFFFFFF;
    d.tid = pid_tgid >> 32;
    d.cpu = bpf_get_smp_processor_id();
    d.type = 40;

    // Send data to user space via perf event
    bpf_perf_event_output(ctx, &events, BPF_F_CURRENT_CPU, &d, sizeof(d));

    return 0;
}
