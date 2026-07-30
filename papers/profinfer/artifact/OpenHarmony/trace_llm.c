// trace_llm.c
#include <stdio.h>
#include <unistd.h>
#include <signal.h>
#include <string.h>
#include <errno.h>
#include <time.h>
#include <bpf/libbpf.h>
#include "trace_llm.h"
#include "trace_llm.skel.h"

static volatile bool exiting = false;
static FILE *csv_fp = NULL;

static int libbpf_print_fn(enum libbpf_print_level level, const char *format, va_list args)
{
    return vfprintf(stderr, format, args);
}

static void sig_handler(int sig)
{
    exiting = true;
}

static void handle_event(void *ctx, int cpu, void *data, __u32 data_sz)
{
    if (__builtin_expect(!csv_fp, 0))
        return;

    const struct data_t *e = data;

    static const char *type_map[40] = {
        [10] = "llama_decode (start)",
        [15] = "llama_decode (end)",
        [20] = "ggml_compute_forward (start)",
        [25] = "ggml_compute_forward (end)",
        [30] = "ggml_backend_graph_compute_async (start)",
        [35] = "ggml_backend_graph_compute_async (end)",
    };

    const char *func_name = "unknown";
    if (e->type < 40 && type_map[e->type])
        func_name = type_map[e->type];

    static char buf[2048];
    int off = 0;

    off += snprintf(buf+off, sizeof(buf)-off,
        "%s,%u,%u,%d,%lu,%d,%d,%s,",
        func_name, e->pid, e->tid, e->cpu, e->Ts,
        e->type, e->op, e->name);

    for (int i = 0; i < 16; i++)
        off += snprintf(buf+off, sizeof(buf)-off,
                        "%d%s", e->guid[i], (i == 15) ? "," : "|");

#ifdef DIMS
    off += snprintf(buf+off, sizeof(buf)-off,
        "0x%lx,0x%lx,0x%lx,0x%lx,"
        "%ld,%ld,%ld,%ld,"
        "%ld,%ld,%ld,%ld,"
        "%ld,%ld,%ld,%ld,"
        "%ld,%ld,%ld,%ld",
        e->tensor_address,
        e->first_src_addr,
        e->second_src_addr,
        e->third_src_addr,
        e->ne0,e->ne1,e->ne2,e->ne3,
        e->src0_ne[0],e->src0_ne[1],e->src0_ne[2],e->src0_ne[3],
        e->src1_ne[0],e->src1_ne[1],e->src1_ne[2],e->src1_ne[3],
        e->src2_ne[0],e->src2_ne[1],e->src2_ne[2],e->src2_ne[3]);
#endif

    fprintf(csv_fp, "%s\n", buf);
}

static void handle_lost(void *ctx, int cpu, __u64 lost_cnt)
{
    fprintf(stderr, "Lost %llu events on CPU %d\n", lost_cnt, cpu);
}

int main(int argc, char **argv)
{
    struct trace_llm_bpf *skel = NULL;
    struct perf_buffer *pb = NULL;
    int err;
    LIBBPF_OPTS(bpf_uprobe_opts, trace_llm_opts);

    libbpf_set_print(libbpf_print_fn);

    // Setup signal handlers
    signal(SIGINT, sig_handler);
    signal(SIGTERM, sig_handler);

    // Create timestamped CSV file
    time_t t = time(NULL);
    struct tm tm_info;
    localtime_r(&t, &tm_info);
    char filename[128];
    strftime(filename, sizeof(filename), "event_log_%Y%m%d_%H%M%S.csv", &tm_info);

    csv_fp = fopen(filename, "w");
    if (!csv_fp) {
        perror("fopen");
        return 1;
    }

    fprintf(csv_fp, "Function,PID,TID,CPU,Timestamp,Type,OP,Name,GUID,Tensor,Src0,Src1,Src2,ne0,ne1,ne2,ne3,"
                    "src0_ne0,src0_ne1,src0_ne2,src0_ne3,"
                    "src1_ne0,src1_ne1,src1_ne2,src1_ne3,"
                    "src2_ne0,src2_ne1,src2_ne2,src2_ne3\n");

    // Load and attach BPF program
    skel = trace_llm_bpf__open_and_load();
    if (!skel) {
        fprintf(stderr, "Failed to open and load BPF skeleton\n");
        return 1;
    }

    // --- Attach uprobes ---
    trace_llm_opts.func_name = "llama_decode";
	trace_llm_opts.retprobe = false;
	skel->links.probe_llama_decode_start = bpf_program__attach_uprobe_opts(skel->progs.probe_llama_decode_start,
        -1 /* self pid */, "/system/lib64/libllama.so",
        0 /* offset for function */,
        &trace_llm_opts /* opts */);
    if (!skel->links.probe_llama_decode_start) {
        err = -errno;
        fprintf(stderr, "Failed to attach uprobe: %d\n", err);
        goto cleanup;
    }

    trace_llm_opts.func_name = "llama_decode";
	trace_llm_opts.retprobe = true;
	skel->links.probe_llama_decode_end = bpf_program__attach_uprobe_opts(skel->progs.probe_llama_decode_end,
        -1 /* self pid */, "/system/lib64/libllama.so",
        0 /* offset for function */,
        &trace_llm_opts /* opts */);
    if (!skel->links.probe_llama_decode_end) {
        err = -errno;
        fprintf(stderr, "Failed to attach uretprobe: %d\n", err);
        goto cleanup;
    }

    trace_llm_opts.func_name = "ggml_compute_forward";
	trace_llm_opts.retprobe = false;
	skel->links.probe_ggml_compute_forward_start = bpf_program__attach_uprobe_opts(skel->progs.probe_ggml_compute_forward_start,
        -1 /* self pid */, "/system/lib64/libggml-cpu.so",
        0 /* offset for function */,
        &trace_llm_opts /* opts */);
    if (!skel->links.probe_ggml_compute_forward_start) {
        err = -errno;
        fprintf(stderr, "Failed to attach uprobe: %d\n", err);
        goto cleanup;
    }

    trace_llm_opts.func_name = "ggml_compute_forward";
	trace_llm_opts.retprobe = true;
	skel->links.probe_ggml_compute_forward_end = bpf_program__attach_uprobe_opts(skel->progs.probe_ggml_compute_forward_end,
        -1 /* self pid */, "/system/lib64/libggml-cpu.so",
        0 /* offset for function */,
        &trace_llm_opts /* opts */);
    if (!skel->links.probe_ggml_compute_forward_end) {
        err = -errno;
        fprintf(stderr, "Failed to attach uprobe: %d\n", err);
        goto cleanup;
    }

    trace_llm_opts.func_name = "ggml_backend_graph_compute_async";
	trace_llm_opts.retprobe = false;
	skel->links.probe_ggml_backend_graph_compute_async_start = bpf_program__attach_uprobe_opts(skel->progs.probe_ggml_backend_graph_compute_async_start,
        -1 /* self pid */, "/system/lib64/libggml-base.so",
        0 /* offset for function */,
        &trace_llm_opts /* opts */);
    if (!skel->links.probe_ggml_backend_graph_compute_async_start) {
        err = -errno;
        fprintf(stderr, "Failed to attach uprobe: %d\n", err);
        goto cleanup;
    }

    trace_llm_opts.func_name = "ggml_backend_graph_compute_async";
	trace_llm_opts.retprobe = true;
	skel->links.probe_ggml_backend_graph_compute_async_end = bpf_program__attach_uprobe_opts(skel->progs.probe_ggml_backend_graph_compute_async_end,
        -1 /* self pid */, "/system/lib64/libggml-base.so",
        0 /* offset for function */,
        &trace_llm_opts /* opts */);
    if (!skel->links.probe_ggml_backend_graph_compute_async_end) {
        err = -errno;
        fprintf(stderr, "Failed to attach uprobe: %d\n", err);
        goto cleanup;
    }

    // --- Initialize perf buffer ---
    pb = perf_buffer__new(bpf_map__fd(skel->maps.events), 8,
                          handle_event, handle_lost, NULL, NULL);
    if (!pb) {
        err = -errno;
        fprintf(stderr, "Failed to create perf buffer: %d\n", err);
        goto cleanup;
    }

    printf("Tracing llama_decode and ggml calls... Press Ctrl-C to stop.\n");
    printf("------------------------------------------------------------\n");

    while (!exiting) {
        err = perf_buffer__poll(pb, 100);
        if (err == -EINTR) {
            err = 0;
            break;
        }
        if (err < 0) {
            fprintf(stderr, "Error polling perf buffer: %d\n", err);
            break;
        }
    }

cleanup:
    if (csv_fp) {
        fflush(csv_fp);
        fclose(csv_fp);
    }
    if (pb)
        perf_buffer__free(pb);
    trace_llm_bpf__destroy(skel);
    return err < 0 ? -err : 0;
}
