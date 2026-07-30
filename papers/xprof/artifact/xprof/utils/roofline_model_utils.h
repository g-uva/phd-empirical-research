#ifndef THIRD_PARTY_XPROF_UTILS_ROOFLINE_MODEL_UTILS_H_
#define THIRD_PARTY_XPROF_UTILS_ROOFLINE_MODEL_UTILS_H_

namespace tensorflow {
namespace profiler {

// Takes flops as Gflops and BW as GiB.
double RidgePoint(double peak_gigaflops_per_second,
                  double peak_gibibytes_per_second);

}  // namespace profiler
}  // namespace tensorflow

#endif  // THIRD_PARTY_XPROF_UTILS_ROOFLINE_MODEL_UTILS_H_
