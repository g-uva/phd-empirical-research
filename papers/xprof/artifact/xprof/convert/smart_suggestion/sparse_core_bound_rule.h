/* Copyright 2025 The TensorFlow Authors. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
==============================================================================*/

#ifndef THIRD_PARTY_XPROF_CONVERT_SMART_SUGGESTION_SPARSE_CORE_BOUND_RULE_H_
#define THIRD_PARTY_XPROF_CONVERT_SMART_SUGGESTION_SPARSE_CORE_BOUND_RULE_H_

#include <optional>
#include <string>

#include "absl/status/statusor.h"
#include "absl/strings/str_cat.h"
#include "absl/strings/str_format.h"
#include "xla/tsl/platform/statusor.h"
#include "xprof/convert/smart_suggestion/signal_provider.h"
#include "xprof/convert/smart_suggestion/constants.h"
#include "xprof/convert/smart_suggestion/smart_suggestion_rule.h"
#include "plugin/xprof/protobuf/smart_suggestion.pb.h"

namespace tensorflow {
namespace profiler {

// Rule to detect high SparseCore time bottleneck.
class SparseCoreBoundRule : public SmartSuggestionRule {
 public:
  bool MeetsConditions(const SignalProvider& signal_provider) const override {
    if (!signal_provider.IsLatencyBound()) {
      return false;
    }

    absl::StatusOr<double> sparse_core_time_percent =
        signal_provider.GetSparseCoreTimePercent();
    if (!sparse_core_time_percent.ok()) {
      return false;
    }

    return *sparse_core_time_percent > kSparseCoreTimeThresholdInPercent;
  }

  absl::StatusOr<std::optional<SmartSuggestion>> GenerateSuggestion(
      const SignalProvider& signal_provider) const override {
    SmartSuggestion suggestion;
    suggestion.set_rule_name("SparseCoreBoundRule");

    TF_ASSIGN_OR_RETURN(double sparse_core_time_percent,
                        signal_provider.GetSparseCoreTimePercent());
    std::string suggestion_text = absl::StrCat(
        "<p>Your program is likely bottlenecked by <b>SparseCore Operations"
        "</b> in the TPU: <b>",
        absl::StrFormat("%.1f", sparse_core_time_percent),
        "% of the total step time </b> is spent on SparseCore. Please consider "
        "the following optimizations: </p>",
        "<ul>"
        "<li><b>Refine Sparse Data Representation:</b> Ensure your sparse "
        "tensors are in the most performant format for your hardware (e.g., "
        "CSR/CSC if suitable). Pre-process data to improve memory access "
        "patterns on the SparseCore, like sorting indices or grouping related "
        "features.</li>"
        "<li><b>Streamline Embedding Tables:</b> For large embedding tables, "
        "consider quantization (reducing precision like int8) or pruning to "
        "significantly cut down their memory footprint and processing load on "
        "the SparseCore.</li>"
        "<li><b>Utilize Framework-Specific Sparse APIs:</b> Employ "
        "specialized APIs designed for sparse operations on your platform "
        "(e.g., tf.tpu.experimental.embedding.TPU Embedding for "
        "TensorFlow/TPU). These are highly optimized for direct SparseCore "
        "interaction.</li>"
        "</ul>");

    suggestion.set_suggestion_text(suggestion_text);
    return suggestion;
  }
};

}  // namespace profiler
}  // namespace tensorflow

#endif  // THIRD_PARTY_XPROF_CONVERT_SMART_SUGGESTION_SPARSE_CORE_BOUND_RULE_H_
