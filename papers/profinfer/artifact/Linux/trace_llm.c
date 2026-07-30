#include <uapi/linux/ptrace.h>
#include <linux/blkdev.h>
#include <linux/sched.h>
// Old version
// #define OFFSET_NE 16
// #define OFFSET_NB 48
// #define OFFSET_OP 80
// #define OFFSET_SRC 160
// #define OFFSET_VIEW_SRC 240
// #define OFFSET_VIEW_OFFS 248

/***********************
 * These macros are for the llama.cpp version b4743
 * Adapt it based on the version of yours
 ***********************/
// Offset in the struct ggml_tensor
#define OFFSET_NE 16
#define OFFSET_NB 48
#define OFFSET_OP 80
#define OFFSET_SRC 152
#define OFFSET_VIEW_SRC 232
#define OFFSET_VIEW_OFFS 240
#define OFFSET_DATA 248
#define OFFSET_NAME 256

// Operator IDs
#define ID_MUL_MAT_ID 27 // RKNN this is 28
/* End of version-specific macros */

/************************
 * These macros are for specific models
 */
#define MAX_NUM_EXPERTS 4
#define MAX_NUM_OPS 128

// TODO: Pass the num_thread as a macro and create BPF_PERF_ARRAY recordingly
// TODO: Consider define a macro function to define all the underlying functions by passing a flag to compile

#ifdef RING_BUFFER
BPF_RINGBUF_OUTPUT(eventsRun, 1);
BPF_RINGBUF_OUTPUT(eventsRunG, 1);
BPF_RINGBUF_OUTPUT(eventsRunO, 1);
#else
BPF_PERF_OUTPUT(eventsRun);
BPF_PERF_OUTPUT(eventsRunG); // For uprobe of graph tracing
BPF_PERF_OUTPUT(eventsRunO); // For uprobe of operator tracing
#endif
#ifdef OPEN_PERF
BPF_PERF_ARRAY(cnt0, NUM_CPUS);
BPF_PERF_ARRAY(cnt1, NUM_CPUS);
#endif
#ifdef TARGET_N_ITER
BPF_ARRAY(num_iter_array, u16, 1);
#endif
// A hash between pid -> op_on flag
BPF_HASH(op_tracing_on, u32, u8, 8);
BPF_HASH(op_tracing_on_rk, u32, u8, 8);
struct op_map_128 {
  u64 lo;
  u64 hi;
};

BPF_ARRAY(activated_ops, struct op_map_128, 1);

struct data_t {
  u64 TS;
  u16 type;
  u32 pid;
  u16 cpu;
  s32 other;
#ifdef OPEN_PERF
  u64 pmc_0;
  u64 pmc_1;
#endif
};

struct o_data_t {
    u64 TS;
    u16 type;
    u32 pid;
    u16 cpu;
    char name[16];
    u16 op;
#ifdef DIMS
    u64 tensor_address;
    u64 first_src_addr, second_src_addr;
    s64 ne0, ne1, ne2, ne3;
    s64 src0_ne[4], src1_ne[4];
#endif

#ifdef TRACE_MOE
  u64 third_src_addr;
  s64 src2_ne[4];
  s32 id_experts[MAX_NUM_EXPERTS];
#endif

#ifdef OPEN_PERF
  u64 pmc_0;
  u64 pmc_1;
#endif
};

struct g_data_t {
  u64 TS;
  u16 type;
  u32 pid;
  u16 cpu;
  u8 guid[16];
#ifdef OPEN_PERF
  u64 pmc_0;
  u64 pmc_1;
#endif
};



int llama_decode_start(struct pt_regs *ctx) {
  u64 ts = bpf_ktime_get_ns();
#ifdef RING_BUFFER
  struct data_t *data = eventsRun.ringbuf_reserve(sizeof(struct data_t));
  if (!data) { // Failed to reserve space
        return 1;
    }
#else
  struct data_t data_ = {};
  struct data_t *data = &data_;
#endif
  data->TS = ts;
  data->pid = bpf_get_current_pid_tgid();
  data->type = 10;
  
  data->cpu = bpf_get_smp_processor_id();
#ifdef OPEN_PERF
  data->pmc_0 = cnt0.perf_read(CUR_CPU_IDENTIFIER);
  // data->pmc_1 = cnt1.perf_read(CUR_CPU_IDENTIFIER);
  data->pmc_1 = cnt1.perf_read(CUR_CPU_IDENTIFIER);
  // data->pmc_hw_2 = cnt_hw_2.perf_read(CUR_CPU_IDENTIFIER);
#endif

#ifdef RING_BUFFER
  eventsRun.ringbuf_submit(data, 0);
#else
  eventsRun.perf_submit(ctx, &data_, sizeof(data_));
#endif
  // if (((s64)val < 0) && ((s64)val > -256))
  //     return 0;
  // prev.update(&cpu, &val);
  return 0;
}

int llama_decode_end(struct pt_regs *ctx) {
  u64 ts = bpf_ktime_get_ns();
#ifdef TARGET_N_ITER
  u32 key = 0;
  u16* num_iter = num_iter_array.lookup(&key);
  if (num_iter) {
    (*num_iter)++;
  }
#endif
#ifdef RING_BUFFER
  struct data_t *data = eventsRun.ringbuf_reserve(sizeof(struct data_t));
  if (!data) { // Failed to reserve space
        return 1;
    }
#else
  struct data_t data_ = {};
  struct data_t *data = &data_;
#endif
  data->TS = ts;
  data->pid = bpf_get_current_pid_tgid();
  data->type = 15;
  data->cpu = bpf_get_smp_processor_id();
#ifdef OPEN_PERF
  data->pmc_0 = cnt0.perf_read(CUR_CPU_IDENTIFIER);
  // data->pmc_1 = cnt1.perf_read(CUR_CPU_IDENTIFIER);
  data->pmc_1 = cnt1.perf_read(CUR_CPU_IDENTIFIER);
  // data->pmc_hw_2 = cnt_hw_2.perf_read(CUR_CPU_IDENTIFIER);
#endif
#ifdef RING_BUFFER
  eventsRun.ringbuf_submit(data, 0);
#else
  eventsRun.perf_submit(ctx, &data_, sizeof(data_));
#endif
  return 0;
}

int ggml_compute_forward_start(struct pt_regs *ctx) {
  u64 ts = bpf_ktime_get_ns();
  u32 key = 0;
#ifdef TARGET_N_ITER
  u16* num_iter = num_iter_array.lookup(&key);
  if (!num_iter || *num_iter != TARGET_N_ITER) {
    bpf_trace_printk("Flag is off");
    return 0;
  }
#endif
  u16 op;
  void* void_ptr_reg_2 = (void *)PT_REGS_PARM2(ctx);
  int ret = 0;
  ret = bpf_probe_read(&op, sizeof(u16), (u16 *)(void_ptr_reg_2 + OFFSET_OP));
  u32 op_u32 = (u32)op;
  struct op_map_128* op_map = activated_ops.lookup(&key);
  if (!op_map) {
    return 0;
  }

#ifdef RING_BUFFER
  struct o_data_t *data = eventsRunO.ringbuf_reserve(sizeof(struct o_data_t));
  if (!data) { // Failed to reserve space
        return 1;
    }
#else
  struct o_data_t data_ = {};
  struct o_data_t *data = &data_;
#endif
  data->TS = ts;
  u32 pid = bpf_get_current_pid_tgid();
  data->pid = pid;
  u64 part = (op_u32 < 64) ? op_map->lo : op_map->hi;
  u32 bit_idx = op_u32 & 63;
  u8 op_is_set = (part & ((__u64)1 << bit_idx)) ? 1 : 0;
  // u8* op_tracing_flag = activated_ops.lookup(&op_u32);
  if (op_is_set) {
    u8 one_flag = 1;
    op_tracing_on.update(&pid, &one_flag);
  } else {
    bpf_trace_printk("Flag is off");
    u8 zero_flag = 0;
    op_tracing_on.update(&pid, &zero_flag);
#ifdef RING_BUFFER
    bpf_ringbuf_discard(data, 0);
#endif
    return 0;
  }
  
  data->type = 20;
  data->cpu = bpf_get_smp_processor_id();
  // // Only probe mul mat, current order is 26
  // if (op != 26) {
  //   bpf_ringbuf_discard(data, 0);
  //   return 1;
  // }
  data->op = op;
  ret = bpf_probe_read(&data->name, sizeof(data->name), (void_ptr_reg_2 + OFFSET_NAME));
#ifdef DIMS
  u64 pointer, first_src_addr, second_src_addr;
  s64 ne0, ne1, ne2, ne3;
  s64 src0_ne[4], src1_ne[4];
  ret = bpf_probe_read(&pointer, sizeof(u64 *), &PT_REGS_PARM2(ctx));
  ret = bpf_probe_read(&first_src_addr, sizeof(u64 *), (u64 *)(void_ptr_reg_2 + OFFSET_SRC));
  ret = bpf_probe_read(&second_src_addr, sizeof(u64 *), (u64 *)(void_ptr_reg_2 + OFFSET_SRC + 8));
  ret = bpf_probe_read(&ne0, sizeof(s64 *), (s64 *)(void_ptr_reg_2 + OFFSET_NE));
  ret = bpf_probe_read(&ne1, sizeof(s64 *), (s64 *)(void_ptr_reg_2 + OFFSET_NE + 8));
  ret = bpf_probe_read(&ne2, sizeof(s64 *), (s64 *)(void_ptr_reg_2 + OFFSET_NE + 16));
  ret = bpf_probe_read(&ne3, sizeof(s64 *), (s64 *)(void_ptr_reg_2 + OFFSET_NE + 24));
  // ne of src1
  for (int i = 0; i < 4; i++) {
    ret = bpf_probe_read(&src0_ne[i], sizeof(s64 *), (void *)first_src_addr + OFFSET_NE + 8 * i);
    data->src0_ne[i] = src0_ne[i];
    ret = bpf_probe_read(&src1_ne[i], sizeof(s64 *), (void *)second_src_addr + OFFSET_NE + 8 * i);
    data->src1_ne[i] = src1_ne[i];
  }
  data->tensor_address = pointer;
  data->first_src_addr = first_src_addr;
  data->second_src_addr = second_src_addr;
  data->ne0 = ne0;
  data->ne1 = ne1;
  data->ne2 = ne2;
  data->ne3 = ne3;
#endif // DIMS
// Only mul_mat_id has three srcs now.
#ifdef TRACE_MOE
if (op == ID_MUL_MAT_ID) {
  u64 third_src_addr;
  s64 src2_ne[4];
  // TODO: parse what are the IDs?
  ret = bpf_probe_read(&third_src_addr, sizeof(u64 *), (u64 *)(void_ptr_reg_2 + OFFSET_SRC + 16));
  data->third_src_addr = third_src_addr;
  for (int i = 0; i < 4; i++) {
    ret = bpf_probe_read(&src2_ne[i], sizeof(s64 *), (void *)third_src_addr + OFFSET_NE + 8 * i);
    data->src2_ne[i] = src2_ne[i];
  }
  // At the moment, the batch scenario is not considered.
  // for (int iid1 = 0; iid1 < src2_ne[1]; iid1++) {
  // }
}
// BUG: Only when getting ts here can take effect.
// data->TS = bpf_ktime_get_ns();

if (data->op == ID_MUL_MAT_ID) {
  u64 data_addr_start, third_src_addr;
  ret = bpf_probe_read(&third_src_addr, sizeof(u64 *), (u64 *)(void_ptr_reg_2 + OFFSET_SRC + 16));
  ret = bpf_probe_read(&data_addr_start, sizeof(u64 *), (u64 *)(third_src_addr + OFFSET_DATA));
  for (int id = 0; id < 4; id++) {
    s32 tmp;
    ret = bpf_probe_read(&tmp, sizeof(s32), (char *)data_addr_start + sizeof(s32) * id);
    data->id_experts[id] = tmp;
  }
}
#endif
#ifdef OPEN_PERF
  data->pmc_0 = cnt0.perf_read(CUR_CPU_IDENTIFIER);
  // data->pmc_1 = cnt1.perf_read(CUR_CPU_IDENTIFIER);
  data->pmc_1 = cnt1.perf_read(CUR_CPU_IDENTIFIER);
  // data->pmc_hw_2 = cnt_hw_2.perf_read(CUR_CPU_IDENTIFIER);
#endif
#ifdef RING_BUFFER
  eventsRunO.ringbuf_submit(data, 0);
#else
  eventsRunO.perf_submit(ctx, &data_, sizeof(data_));
#endif

  return 0;
}

int ggml_compute_forward_end(struct pt_regs *ctx) {
  u64 ts = bpf_ktime_get_ns();
  u32 pid = bpf_get_current_pid_tgid();
#ifdef TARGET_N_ITER
  u32 key = 0;
  u16* num_iter = num_iter_array.lookup(&key);
  if (!num_iter || *num_iter != TARGET_N_ITER) {
    bpf_trace_printk("Flag is off");
    return 0;
  }
#endif
  u8* op_tracing_flag = op_tracing_on.lookup(&pid);
  if (!op_tracing_flag || *op_tracing_flag == 0) {
    bpf_trace_printk("Flag is off");
    return 0;
  }
#ifdef RING_BUFFER
  struct data_t *data = eventsRun.ringbuf_reserve(sizeof(struct data_t));
  if (!data) { // Failed to reserve space
        return 1;
    }
#else
  struct data_t data_ = {};
  struct data_t *data = &data_;
#endif
  data->TS = ts;
  data->pid = pid;

  data->type = 25;
  data->cpu = bpf_get_smp_processor_id();
  int ret;
#ifdef OPEN_PERF
  data->pmc_0 = cnt0.perf_read(CUR_CPU_IDENTIFIER);
  // data->pmc_1 = cnt1.perf_read(CUR_CPU_IDENTIFIER);
  data->pmc_1 = cnt1.perf_read(CUR_CPU_IDENTIFIER);
  // data->pmc_hw_2 = cnt_hw_2.perf_read(CUR_CPU_IDENTIFIER);
#endif
  
#ifdef RING_BUFFER
  eventsRun.ringbuf_submit(data, 0);
#else
  eventsRun.perf_submit(ctx, &data_, sizeof(data_));
#endif

  return 0;
}

int ggml_backend_graph_compute_async_start(struct pt_regs *ctx) {
  bpf_trace_printk("graph_compute");
  u64 ts = bpf_ktime_get_ns();
#ifdef RING_BUFFER
  struct g_data_t *data = eventsRunG.ringbuf_reserve(sizeof(struct g_data_t));
  if (!data) { // Failed to reserve space
        return 1;
    }
#else
  struct g_data_t data_ = {};
  struct g_data_t *data = &data_;
#endif
  data->TS = bpf_ktime_get_ns();
  data->pid = bpf_get_current_pid_tgid();
  data->type = 30;
  data->cpu = bpf_get_smp_processor_id();
int ret = 0;
u64 ggml_backend_ptr_addr, guid_ptr_addr;
ret = bpf_probe_read(&ggml_backend_ptr_addr, sizeof(u64*), &PT_REGS_PARM1(ctx));
ret = bpf_probe_read(&guid_ptr_addr, sizeof(u64*), (void*)ggml_backend_ptr_addr);
ret = bpf_probe_read(&data->guid, sizeof(data->guid), (void*)guid_ptr_addr);
#ifdef OPEN_PERF
  data->pmc_0 = cnt0.perf_read(CUR_CPU_IDENTIFIER);
  data->pmc_1 = cnt1.perf_read(CUR_CPU_IDENTIFIER);
#endif
#ifdef RING_BUFFER
  eventsRunG.ringbuf_submit(data, 0);
#else
  eventsRunG.perf_submit(ctx, &data_, sizeof(data_));
#endif
  return 0;
}

int ggml_backend_graph_compute_async_end(struct pt_regs *ctx) {
  u64 ts = bpf_ktime_get_ns();
#ifdef RING_BUFFER
  struct data_t *data = eventsRun.ringbuf_reserve(sizeof(struct data_t));
  if (!data) { // Failed to reserve space
        return 1;
    }
#else
  struct data_t data_ = {};
  struct data_t *data = &data_;
#endif
  data->TS = ts;
  data->pid = bpf_get_current_pid_tgid();
  data->type = 35;
  
  data->cpu = bpf_get_smp_processor_id();
#ifdef OPEN_PERF
  data->pmc_0 = cnt0.perf_read(CUR_CPU_IDENTIFIER);
  data->pmc_1 = cnt1.perf_read(CUR_CPU_IDENTIFIER);
#endif
#ifdef RING_BUFFER
  eventsRun.ringbuf_submit(data, 0);
#else
  eventsRun.perf_submit(ctx, &data_, sizeof(data_));
#endif
  return 0;
}

int ggml_compute_forward_acc_start(struct pt_regs *ctx) {
  u64 ts = bpf_ktime_get_ns();
  u32 key = 0;
#ifdef TARGET_N_ITER
  u16* num_iter = num_iter_array.lookup(&key);
  if (!num_iter || *num_iter != TARGET_N_ITER) {
    bpf_trace_printk("Flag is off");
    return 0;
  }
#endif
  u16 op;
  void* void_ptr_reg_2 = (void *)PT_REGS_PARM2(ctx);
  int ret = 0;
  ret = bpf_probe_read(&op, sizeof(u16), (u16 *)(void_ptr_reg_2 + OFFSET_OP));
  u32 op_u32 = (u32)op;
  struct op_map_128* op_map = activated_ops.lookup(&key);
  if (!op_map) {
    return 0;
  }

#ifdef RING_BUFFER
  struct o_data_t *data = eventsRunO.ringbuf_reserve(sizeof(struct o_data_t));
  if (!data) { // Failed to reserve space
        return 1;
    }
#else
  struct o_data_t data_ = {};
  struct o_data_t *data = &data_;
#endif
  data->TS = ts;
  u32 pid = bpf_get_current_pid_tgid();
  data->pid = pid;
  u64 part = (op_u32 < 64) ? op_map->lo : op_map->hi;
  u32 bit_idx = op_u32 & 63;
  u8 op_is_set = (part & ((__u64)1 << bit_idx)) ? 1 : 0;
  // u8* op_tracing_flag = activated_ops.lookup(&op_u32);
  if (op_is_set) {
    u8 one_flag = 1;
    op_tracing_on_rk.update(&pid, &one_flag);
  } else {
    bpf_trace_printk("Flag is off");
    u8 zero_flag = 0;
    op_tracing_on_rk.update(&pid, &zero_flag);
#ifdef RING_BUFFER
    bpf_ringbuf_discard(data, 0);
#endif
    return 0;
  }
  
  data->type = 40;
  data->cpu = bpf_get_smp_processor_id();
  // // Only probe mul mat, current order is 26
  // if (op != 26) {
  //   bpf_ringbuf_discard(data, 0);
  //   return 1;
  // }
  data->op = op;
  ret = bpf_probe_read(&data->name, sizeof(data->name), (void_ptr_reg_2 + OFFSET_NAME));
#ifdef DIMS
  u64 pointer, first_src_addr, second_src_addr;
  s64 ne0, ne1, ne2, ne3;
  s64 src0_ne[4], src1_ne[4];
  ret = bpf_probe_read(&pointer, sizeof(u64 *), &PT_REGS_PARM2(ctx));
  ret = bpf_probe_read(&first_src_addr, sizeof(u64 *), (u64 *)(void_ptr_reg_2 + OFFSET_SRC));
  ret = bpf_probe_read(&second_src_addr, sizeof(u64 *), (u64 *)(void_ptr_reg_2 + OFFSET_SRC + 8));
  ret = bpf_probe_read(&ne0, sizeof(s64 *), (s64 *)(void_ptr_reg_2 + OFFSET_NE));
  ret = bpf_probe_read(&ne1, sizeof(s64 *), (s64 *)(void_ptr_reg_2 + OFFSET_NE + 8));
  ret = bpf_probe_read(&ne2, sizeof(s64 *), (s64 *)(void_ptr_reg_2 + OFFSET_NE + 16));
  ret = bpf_probe_read(&ne3, sizeof(s64 *), (s64 *)(void_ptr_reg_2 + OFFSET_NE + 24));
  // ne of src1
  for (int i = 0; i < 4; i++) {
    ret = bpf_probe_read(&src0_ne[i], sizeof(s64 *), (void *)first_src_addr + OFFSET_NE + 8 * i);
    data->src0_ne[i] = src0_ne[i];
    ret = bpf_probe_read(&src1_ne[i], sizeof(s64 *), (void *)second_src_addr + OFFSET_NE + 8 * i);
    data->src1_ne[i] = src1_ne[i];
  }
  data->tensor_address = pointer;
  data->first_src_addr = first_src_addr;
  data->second_src_addr = second_src_addr;
  data->ne0 = ne0;
  data->ne1 = ne1;
  data->ne2 = ne2;
  data->ne3 = ne3;
#endif // DIMS
// Only mul_mat_id has three srcs now.
#ifdef TRACE_MOE
if (op == ID_MUL_MAT_ID) {
  u64 third_src_addr;
  s64 src2_ne[4];
  // TODO: parse what are the IDs?
  ret = bpf_probe_read(&third_src_addr, sizeof(u64 *), (u64 *)(void_ptr_reg_2 + OFFSET_SRC + 16));
  data->third_src_addr = third_src_addr;
  for (int i = 0; i < 4; i++) {
    ret = bpf_probe_read(&src2_ne[i], sizeof(s64 *), (void *)third_src_addr + OFFSET_NE + 8 * i);
    data->src2_ne[i] = src2_ne[i];
  }
  // At the moment, the batch scenario is not considered.
  // for (int iid1 = 0; iid1 < src2_ne[1]; iid1++) {
  // }
}

// BUG: Only when getting ts here can take effect.
// data->TS = bpf_ktime_get_ns();
if (data->op == ID_MUL_MAT_ID) {
  u64 data_addr_start, third_src_addr;
  ret = bpf_probe_read(&third_src_addr, sizeof(u64 *), (u64 *)(void_ptr_reg_2 + OFFSET_SRC + 16));
  ret = bpf_probe_read(&data_addr_start, sizeof(u64 *), (u64 *)(third_src_addr + OFFSET_DATA));
  for (int id = 0; id < MAX_NUM_EXPERTS; id++) {
    s32 tmp;
    ret = bpf_probe_read(&tmp, sizeof(s32), (char *)data_addr_start + sizeof(s32) * id);
    data->id_experts[id] = tmp;
  }
}
#endif
#ifdef OPEN_PERF
  data->pmc_0 = cnt0.perf_read(CUR_CPU_IDENTIFIER);
  // data->pmc_1 = cnt1.perf_read(CUR_CPU_IDENTIFIER);
  data->pmc_1 = cnt1.perf_read(CUR_CPU_IDENTIFIER);
  // data->pmc_hw_2 = cnt_hw_2.perf_read(CUR_CPU_IDENTIFIER);
#endif
#ifdef RING_BUFFER
  eventsRunO.ringbuf_submit(data, 0);
#else
  eventsRunO.perf_submit(ctx, &data_, sizeof(data_));
#endif

  return 0;
}

int ggml_compute_forward_acc_end(struct pt_regs *ctx) {
  u64 ts = bpf_ktime_get_ns();
  u32 pid = bpf_get_current_pid_tgid();
#ifdef TARGET_N_ITER
  u32 key = 0;
  u16* num_iter = num_iter_array.lookup(&key);
  if (!num_iter || *num_iter != TARGET_N_ITER) {
    bpf_trace_printk("Flag is off");
    return 0;
  }
#endif
#ifdef RING_BUFFER
  struct data_t *data = eventsRun.ringbuf_reserve(sizeof(struct data_t));
  if (!data) { // Failed to reserve space
        return 1;
    }
#else
  struct data_t data_ = {};
  struct data_t *data = &data_;
#endif
  data->TS = ts;
  data->pid = pid;
  u8* op_tracing_flag = op_tracing_on_rk.lookup(&pid);
  if (!op_tracing_flag || *op_tracing_flag == 0) {
    bpf_trace_printk("Flag is off");
#ifdef RING_BUFFER
    bpf_ringbuf_discard(data, 0);
#endif
    return 0;
  }
  data->type = 45;
  data->cpu = bpf_get_smp_processor_id();
  int ret;
#ifdef OPEN_PERF
  data->pmc_0 = cnt0.perf_read(CUR_CPU_IDENTIFIER);
  // data->pmc_1 = cnt1.perf_read(CUR_CPU_IDENTIFIER);
  data->pmc_1 = cnt1.perf_read(CUR_CPU_IDENTIFIER);
  // data->pmc_hw_2 = cnt_hw_2.perf_read(CUR_CPU_IDENTIFIER);
#endif
  
#ifdef RING_BUFFER
  eventsRun.ringbuf_submit(data, 0);
#else
  eventsRun.perf_submit(ctx, &data_, sizeof(data_));
#endif

  return 0;
}

int compute_submat_mul_start(struct pt_regs *ctx)
{
  u64 ts = bpf_ktime_get_ns();
#ifdef RING_BUFFER
  struct data_t *data = eventsRun.ringbuf_reserve(sizeof(struct data_t));
  if (!data) { // Failed to reserve space
        return 1;
    }
#else
  struct data_t data_ = {};
  struct data_t *data = &data_;
#endif
  

#ifdef TARGET_N_ITER
  u32 key = 0;
  u16* num_iter = num_iter_array.lookup(&key);
  if (!num_iter || *num_iter <= TARGET_N_ITER) {
    bpf_trace_printk("Flag is off");
    return 0;
  } else {
    s32 n_cores = 2;
    int ret = bpf_probe_write_user((void *)PT_REGS_PARM1(ctx), &n_cores, sizeof(s32));
    bpf_trace_printk("AFTER N ITER");
  }
#endif
  int ret = bpf_probe_read(&data->other, sizeof(s32), (void *)PT_REGS_PARM1(ctx));
  data->type = 50;
  data->cpu = bpf_get_smp_processor_id();

#ifdef RING_BUFFER
  eventsRun.ringbuf_submit(data, 0);
#else
  eventsRun.perf_submit(ctx, &data_, sizeof(data_));
#endif
  return 0;
};

int compute_submat_mul_end(struct pt_regs *ctx)
{
#ifdef RING_BUFFER
  struct data_t *data = eventsRun.ringbuf_reserve(sizeof(struct data_t));
  if (!data) { // Failed to reserve space
        return 1;
    }
#else
  struct data_t data_ = {};
  struct data_t *data = &data_;
#endif
  u64 ts = bpf_ktime_get_ns();
  u32 pid = bpf_get_current_pid_tgid();
  data->type = 55;
  data->cpu = bpf_get_smp_processor_id();
#ifdef RING_BUFFER
  eventsRun.ringbuf_submit(data, 0);
#else
  eventsRun.perf_submit(ctx, &data_, sizeof(data_));
#endif
  return 0;
};