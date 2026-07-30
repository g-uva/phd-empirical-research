#ifndef THIRD_PARTY_XPROF_CONVERT_XPROF_THREAD_POOL_EXECUTOR_H_
#define THIRD_PARTY_XPROF_CONVERT_XPROF_THREAD_POOL_EXECUTOR_H_

#include <functional>
#include <memory>
#include <string>

#include "xla/tsl/platform/threadpool.h"
#include "tsl/platform/cpu_info.h"
#include "xprof/convert/executor.h"

namespace tensorflow {
namespace profiler {

// An implementation of the Executor interface using tsl::thread::ThreadPool.
class XprofThreadPoolExecutor : public Executor {
 public:
  // Creates a XProfThreadPoolExecutor.
  // name: The name for the underlying thread pool.
  // num_threads: The number of threads to use. If 0, it attempts to use
  //              std::thread::hardware_concurrency(). If that also returns 0,
  //              it defaults to 1. It always uses at least 1 thread.
  XprofThreadPoolExecutor(const std::string& name,
                          int num_threads = tsl::port::MaxParallelism());

  // The destructor automatically joins all threads if JoinAll() hasn't been
  // called explicitly.
  ~XprofThreadPoolExecutor() override;

  // Executes the given function using the underlying thread pool's Schedule
  // method.
  void Execute(std::function<void()> fn) override;

  // Waits for all scheduled functions to complete by destroying the underlying
  // thread pool. After calling this, Execute() will no longer schedule tasks.
  void JoinAll() override;

 private:
  std::unique_ptr<tsl::thread::ThreadPool> thread_pool_;
};

}  // namespace profiler
}  // namespace tensorflow

#endif  // THIRD_PARTY_XPROF_CONVERT_XPROF_THREAD_POOL_EXECUTOR_H_
