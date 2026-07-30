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

#ifndef THIRD_PARTY_XPROF_CONVERT_SMART_SUGGESTION_SMART_SUGGESTION_RULE_H_
#define THIRD_PARTY_XPROF_CONVERT_SMART_SUGGESTION_SMART_SUGGESTION_RULE_H_

#include <optional>

#include "absl/status/statusor.h"
#include "xprof/convert/smart_suggestion/signal_provider.h"
#include "plugin/xprof/protobuf/smart_suggestion.pb.h"

namespace tensorflow {
namespace profiler {

// Interface for a smart suggestion rule
class SmartSuggestionRule {
 public:
  virtual ~SmartSuggestionRule() = default;

  // It checks if the rule can be applied, if the conditions are met,
  // and then generates suggestions.
  absl::StatusOr<std::optional<SmartSuggestion>> Apply(
      const SignalProvider& signal_provider) const {
    if (MeetsConditions(signal_provider)) {
      return GenerateSuggestion(signal_provider);
    }
    return std::nullopt;
  }

 protected:
  // Checks if this rule can be applied based on the provided signals and rule's
  // conditions are met to generate a suggestion.
  virtual bool MeetsConditions(const SignalProvider& signal_provider) const = 0;

  // Checks conditions and generates a suggestion.
  virtual absl::StatusOr<std::optional<SmartSuggestion>>
  GenerateSuggestion(const SignalProvider& signal_provider) const = 0;
};

}  // namespace profiler
}  // namespace tensorflow

#endif  // THIRD_PARTY_XPROF_CONVERT_SMART_SUGGESTION_SMART_SUGGESTION_RULE_H_
