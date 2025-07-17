# ThreadPool

Lilya is built on top of an asynchronous event loop (via ASGI). If you write an endpoint or background task as
a regular synchronous function (using `def`), and it does any blocking work (CPU‑bound computations,
I/O that doesn’t release the loop, etc.), it would freeze the entire server until it finishes.

To prevent this, Lilya transparently offloads your blocking code into worker threads so your main event loop
stays free to handle other requests!

Under the hood, Lilya delegates all synchronous calls to AnyIO’s thread‑pool runner:

```python
anyio.to_thread.run_sync(your_sync_function, *args, **kwargs)
```

This ensures that:

* Your synchronous code runs safely in a separate thread.
* The main event loop remains responsive.

---

## How the Thread Pool Works

1. **Submission**
    Whenever Lilya sees a `def` endpoint or a `Task` defined with a synchronous function, it wraps your function
    call in `anyio.to_thread.run_sync()`.

2. **Execution in Worker Threads**
   `run_sync` submits the function to a shared thread pool. The event loop continues handling other tasks.

3. **Result Delivery**
   When the thread finishes, `run_sync` funnels the return value (or exception) back into your async
   flow so your response can be returned or your background task can be marked complete.

---

## What Are “Tokens” (and Why They Matter)?

AnyIO’s thread pool is *bounded*. It uses a token-based limiter to prevent you from endlessly spawning OS
threads and overwhelming your machine.

* **Token** = permission to run one blocking operation in the pool.
* **Default pool size** = **40 tokens**.

  * At most 40 blocking calls can run concurrently.
  * If you submit a 41st, it waits (queues) until a token frees up.

This default is generally safe for typical web workloads (where most endpoints are async).
But if your app has many long‑running synchronous tasks (e.g., heavy data crunching, large file processing),
you may hit this limit and see requests stall until a thread frees up.

---

## Adjusting the Pool Size

You can increase (or decrease) the number of concurrent threads by tweaking the pool’s token count at startup:

```python
import anyio.to_thread

# Grab the global thread limiter…
limiter = anyio.to_thread.current_default_thread_limiter()

# …then set how many threads you want
limiter.total_tokens = 100
```

### When to Tweak

* **Increase** if you expect many simultaneous blocking tasks and you’re not seeing CPU/memory issues.
* **Decrease** if you want to conserve memory or limit parallelism on a resource‑constrained host.

---

## Performance and Memory Considerations

* **More threads** → **more memory usage** (each thread has its own stack).
* **More active threads** → **more context‑switching overhead** → **potentially lower throughput**
if threads compete heavily for CPU.

!!! Tip
    * Profile with real‑world traffic (e.g., via [locust](https://locust.io/) or [wrk](https://github.com/wg/wrk)).
    * Monitor your CPU and memory as you adjust `total_tokens`.

---

## Putting It All Together: A Complete Example

```python
from lilya.apps import Lilya
from lilya.background import Tasks
from lilya.responses import JSONResponse
import anyio.to_thread
import time

app = Lilya()

# ↑→ Increase thread pool size before the app handles any requests
limiter = anyio.to_thread.current_default_thread_limiter()
limiter.total_tokens = 80  # bump from 40 to 80

def blocking_task(name: str, delay: float) -> None:
    """Simulate a long-running, blocking operation."""
    time.sleep(delay)
    print(f"Task {name} completed in {delay}s")

@app.get("/compute/{item_id}")
def compute_endpoint(item_id: int):
    # runs in a thread so the event loop won't block
    result = heavy_computation(item_id)
    return {"item_id": item_id, "result": result}

@app.get("/start-background")
async def start_background():
    background_tasks = Tasks(as_group=True)
    # schedule blocking_task in a thread pool
    background_tasks.add_task(blocking_task, name="BG1", delay=5)
    return JSONResponse({"status": "Background task scheduled!"}, background=background_tasks)
```

1. **At import time**, we grab and resize the thread pool.
2. **`compute_endpoint`** runs `heavy_computation` inside a worker thread.
3. **`start-background`** uses Lilya’s `Tasks` helper, which likewise invokes `anyio.to_thread.run_sync`.

---

## Key Takeaways

* **Lilya auto‑offloads** any `def` endpoints or background tasks to a thread pool.
* **Default pool size = 40** concurrent threads/tokens.
* **Customize** with `current_default_thread_limiter().total_tokens`.
* **Watch performance**: more threads = more memory & context switches.

By understanding and tuning the thread‑pool settings, you can safely mix synchronous code in your
high‑performance, asynchronous Lilya (or FastAPI) applications—without worrying that a single blocking
call will grind your server to a halt.
