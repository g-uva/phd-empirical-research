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

#ifndef THIRD_PARTY_XPROF_UTILS_XPROF_GPU_COST_ANALYSIS_TYPES_H_
#define THIRD_PARTY_XPROF_UTILS_XPROF_GPU_COST_ANALYSIS_TYPES_H_

#include "absl/strings/string_view.h"
#include "xla/service/hlo_cost_analysis.h"
#include "xprof/utils/hlo_cost_analysis_wrapper.h"



namespace tensorflow {
namespace profiler {

struct XprofGpuCostAnalysisConfig
    : public ::tensorflow::profiler::CostAnalysisConfig {
  xla::HloCostAnalysis::Options options;
  XprofGpuCostAnalysisConfig() = default;
  XprofGpuCostAnalysisConfig(xla::HloCostAnalysis::Options options)
      : options(options) {}
  XprofGpuCostAnalysisConfig(const XprofGpuCostAnalysisConfig&) = delete;
  XprofGpuCostAnalysisConfig& operator=(const XprofGpuCostAnalysisConfig&) =
      delete;
  ~XprofGpuCostAnalysisConfig() override = default;
};

inline constexpr absl::string_view kXprofGpuCostAnalysisName =
    "XprofGpuCostAnalysis";

}  // namespace profiler
}  // namespace tensorflow

#endif  // THIRD_PARTY_XPROF_UTILS_XPROF_GPU_COST_ANALYSIS_TYPES_H_
