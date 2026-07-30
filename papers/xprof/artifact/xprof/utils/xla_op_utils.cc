#include "xprof/utils/xla_op_utils.h"

#include <memory>
#include <string>

#include "absl/log/log.h"
#include "absl/status/statusor.h"
#include "absl/strings/match.h"
#include "absl/strings/string_view.h"
#include "nlohmann/json.hpp"
#include "xla/hlo/ir/hlo_instruction.h"
#include "xla/hlo/ir/hlo_module.h"
#include "xla/hlo/parser/hlo_parser.h"

namespace tensorflow {
namespace profiler {

std::string ExtractXprofKernelMetadata(absl::string_view hlo_expression) {
  if (!absl::StrContains(hlo_expression, "xprof_metadata")) {
    return "";
  }
  xla::HloParserOptions options;
  options.set_fill_missing_layouts(false);
  absl::StatusOr<std::unique_ptr<xla::HloModule>> hlo_module =
      xla::ParseAndReturnUnverifiedModule(hlo_expression,
                                          /*config=*/{}, options);
  if (!hlo_module.ok()) {
    LOG_EVERY_N_SEC(ERROR, 1)
        << "Failed to parse HLO module: " << hlo_module.status();
    return "";
  }
  const xla::HloInstruction* instruction =
      hlo_module->get()->entry_computation()->root_instruction();
  const xla::FrontendAttributes& frontend_attributes =
      instruction->frontend_attributes();
  if (frontend_attributes.map().contains("kernel_metadata")) {
    nlohmann::json kernel_metadata =
        nlohmann::json::parse(frontend_attributes.map().at("kernel_metadata"),
                              /*cb=*/nullptr, /*allow_exceptions=*/false);
    if (!kernel_metadata.is_discarded() &&
        kernel_metadata.contains("xprof_metadata")) {
      nlohmann::json xprof_metadata = kernel_metadata["xprof_metadata"];
      if (xprof_metadata.is_string()) {
        xprof_metadata =
            nlohmann::json::parse(xprof_metadata.get<std::string>(),
                                  /*cb=*/nullptr, /*allow_exceptions=*/false);
      }
      if (!xprof_metadata.is_discarded()) {
        return xprof_metadata.dump();
      }
    }
  }
  return "";
}

}  // namespace profiler
}  // namespace tensorflow
