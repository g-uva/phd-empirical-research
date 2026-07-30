#ifndef THIRD_PARTY_XPROF_CONVERT_SOURCE_INFO_UTILS_H_
#define THIRD_PARTY_XPROF_CONVERT_SOURCE_INFO_UTILS_H_

#include <string>

#include "absl/strings/str_cat.h"
#include "absl/strings/str_replace.h"
#include "absl/strings/string_view.h"
#include "plugin/xprof/protobuf/source_info.pb.h"

namespace tensorflow {
namespace profiler {

// Helper function to escape HTML special characters.
inline std::string EscapeHtml(absl::string_view sp) {
  return absl::StrReplaceAll(sp, {{"&", "&amp;"},
                                  {"<", "&lt;"},
                                  {">", "&gt;"},
                                  {"\"", "&quot;"},
                                  {"'", "&#39;"}});
}

// Helper function to format source info
inline std::string SourceInfoFormattedText(
    const tensorflow::profiler::SourceInfo& source_info) {
  if (source_info.file_name().empty() || source_info.line_number() == -1)
    return "";
  // `title` attribute is used to show the full stack trace in the tooltip.
  return absl::StrCat("<div class='source-info-cell' title='",
                      EscapeHtml(source_info.stack_frame()), "'>",
                      EscapeHtml(source_info.file_name()), ":",
                      source_info.line_number(), "</div>");
}

}  // namespace profiler
}  // namespace tensorflow

#endif  // THIRD_PARTY_XPROF_CONVERT_SOURCE_INFO_UTILS_H_
