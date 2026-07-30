#ifndef THIRD_PARTY_XPROF_UTILS_CUSTOM_CALL_UTILS_H_
#define THIRD_PARTY_XPROF_UTILS_CUSTOM_CALL_UTILS_H_

#include <string>

#include "absl/status/statusor.h"
#include "mlir/include/mlir/IR/MLIRContext.h"
#include "xla/hlo/ir/hlo_instruction.h"

namespace xprof {

// Returns the custom call text from the HloInstruction for XLA:TPU.
absl::StatusOr<std::string> GetCustomCallText(
    const xla::HloInstruction& hlo_instruction);

absl::StatusOr<std::string> GetCustomCallText(
    const xla::HloInstruction& hlo_instruction, mlir::MLIRContext& context);

}  // namespace xprof

#endif  // THIRD_PARTY_XPROF_UTILS_CUSTOM_CALL_UTILS_H_
