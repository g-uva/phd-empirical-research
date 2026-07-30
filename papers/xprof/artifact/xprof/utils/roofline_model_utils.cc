#include "xprof/utils/roofline_model_utils.h"

#include "xla/tsl/profiler/utils/math_utils.h"

namespace tensorflow {
namespace profiler {

double RidgePoint(double peak_gigaflops_per_second,
                  double peak_gibibytes_per_second) {
  return tsl::profiler::SafeDivide(
      peak_gigaflops_per_second,
      tsl::profiler::GibiToGiga(peak_gibibytes_per_second));
}

}  // namespace profiler
}  // namespace tensorflow
