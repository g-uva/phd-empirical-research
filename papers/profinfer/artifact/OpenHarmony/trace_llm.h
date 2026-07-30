#ifndef __TRACE_LLM_H
#define __TRACE_LLM_H

// Use ring buffer to send events to user-space
struct data_t {
    uint64_t Ts;
    uint32_t pid;
    uint32_t tid;
    uint16_t cpu;
    uint16_t type; // 10 == decode_start
    // pad to 64 bytes if you want (optional)
    char name[16];
    uint16_t op;
#ifdef DIMS
    uint64_t tensor_address;
    uint64_t first_src_addr, second_src_addr, third_src_addr;
    int64_t ne0, ne1, ne2, ne3;
    int64_t src0_ne[4], src1_ne[4], src2_ne[4];
#endif

#ifdef TRACE_MOE
    int32_t id_experts[4];
#endif

    uint8_t guid[16];

};

#endif /* __TRACE_LLM_H */