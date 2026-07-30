#ifndef THIRD_PARTY_XPROF_CONVERT_EXECUTOR_H_
#define THIRD_PARTY_XPROF_CONVERT_EXECUTOR_H_

#include <functional>

namespace tensorflow {
namespace profiler {

// Interface for abstracting execution mechanisms like thread pools.
class Executor {
 public:
  virtual ~Executor() = default;

  // Executes the given function, potentially in parallel.
  // The execution might happen asynchronously.
  virtual void Execute(std::function<void()> fn) = 0;

  // Waits for all previously scheduled functions via Execute() to complete.
  virtual void JoinAll() = 0;
};

}  // namespace profiler
}  // namespace tensorflow

#endif  // THIRD_PARTY_XPROF_CONVERT_EXECUTOR_H_
