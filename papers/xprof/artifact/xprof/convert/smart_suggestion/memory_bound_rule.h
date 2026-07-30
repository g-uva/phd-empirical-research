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

#ifndef THIRD_PARTY_XPROF_CONVERT_SMART_SUGGESTION_MEMORY_BOUND_RULE_H_
#define THIRD_PARTY_XPROF_CONVERT_SMART_SUGGESTION_MEMORY_BOUND_RULE_H_

#include <optional>
#include <string>

#include "absl/status/statusor.h"
#include "absl/strings/str_cat.h"
#include "absl/strings/str_format.h"
#include "xla/tsl/platform/statusor.h"
#include "xprof/convert/smart_suggestion/constants.h"
#include "xprof/convert/smart_suggestion/signal_provider.h"
#include "xprof/convert/smart_suggestion/smart_suggestion_rule.h"
#include "plugin/xprof/protobuf/smart_suggestion.pb.h"

namespace tensorflow {
namespace profiler {

// Rule to detect memory operations bottleneck.
class MemoryBoundRule : public SmartSuggestionRule {
 public:
  bool MeetsConditions(const SignalProvider& signal_provider) const override {
    absl::StatusOr<double> hbm_utilization_percent =
        signal_provider.GetHbmUtilization();
    absl::StatusOr<double> mxu_utilization_percent =
        signal_provider.GetMxuUtilization();
    if (!hbm_utilization_percent.ok() || !mxu_utilization_percent.ok()) {
      return false;
    }

    return *hbm_utilization_percent > kHbmUtilizationHighThreshold &&
           *mxu_utilization_percent < kMxuUtilizationLowThreshold;
  }

  absl::StatusOr<std::optional<SmartSuggestion>> GenerateSuggestion(
      const SignalProvider& signal_provider) const override {
    SmartSuggestion suggestion;
    suggestion.set_rule_name("MemoryBoundRule");

    TF_ASSIGN_OR_RETURN(double hbm_utilization_percent,
                        signal_provider.GetHbmUtilization());
    TF_ASSIGN_OR_RETURN(double mxu_utilization_percent,
                        signal_provider.GetMxuUtilization());

    std::string suggestion_text = absl::StrCat(
        "<p>Your program is likely bottlenecked by <b>Memory Operations</b>: "
        "High HBM Bandwidth utilization of <b>",
        absl::StrFormat("%.1f", hbm_utilization_percent),
        "%</b> and low MXU utilization of <b>",
        absl::StrFormat("%.1f", mxu_utilization_percent),
        "%</b> indicates that processors are often waiting for data. Please "
        "consider the following optimizations:</p>",
        "<ul>"
        "<li><b>Increase the Batch Size:</b> A larger batch size increases the "
        "computational work (the matrix multiplications in your model) done "
        "for each data loading step. This improves the ratio of computation to "
        "memory access, which should directly increase MXU utilization.</li>"
        "<li><b>Utilize Gradient Accumulation:</b> This technique processes "
        "several smaller batches sequentially and only updates the model "
        "weights after accumulating the gradients from all of them. This "
        "simulates a larger effective batch size without a proportional "
        "increase in memory usage.</li>"
        "<li><b>Increase Model Depth or Width:</b> Make the model larger by "
        "adding more layers or increasing the size of the hidden dimensions to "
        "improve the MXU utilization.</li>"
        "<li><b>Optimize the Data Format:</b> Store your dataset in a format "
        "optimized for high-throughput reads, such as TFRecord for TensorFlow "
        "or Petastorm for PyTorch. These formats are more efficient than "
        "reading individual image or text files.</li>"
        "</ul>");

    suggestion.set_suggestion_text(suggestion_text);
    return suggestion;
  }
};

}  // namespace profiler
}  // namespace tensorflow

#endif  // THIRD_PARTY_XPROF_CONVERT_SMART_SUGGESTION_MEMORY_BOUND_RULE_H_
