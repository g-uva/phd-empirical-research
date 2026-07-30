/* Copyright 2020 The TensorFlow Authors. All Rights Reserved.

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
#ifndef XPROF_UTILS_COST_UTILS_H_
#define XPROF_UTILS_COST_UTILS_H_

#include <algorithm>
#include <cstdint>
#include "xla/tsl/profiler/utils/xplane_visitor.h"

namespace tensorflow {
namespace profiler {

using ::tsl::profiler::XEventVisitor;

// Returns 0 in case a cost returned by HloCostAnalysis is -1.
// HloCostAnalysis returns -1 if the instruction does not have a cost.
// Other negative costs could be adjustment for higher precision cost analysis.
inline int64_t ValidHloCost(int64_t cost) { return cost == -1 ? 0 : cost; }

}  // namespace profiler
}  // namespace tensorflow

#endif  // XPROF_UTILS_COST_UTILS_H_
