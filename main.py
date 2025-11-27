import asyncio
import aiohttp
import time
import os

sent = 0

async def worker(session, url):
    global sent
    while True:
        try:
            async with session.get(url):
                sent += 1
        except:
            pass

async def monitor():
    global sent
    old = 0
    while True:
        await asyncio.sleep(1)
        rps = sent - old
        old = sent
        print(f"[RPS: {rps}]  Total: {sent}")

async def main():
    global sent

    # اطلب الرابط من المستخدم
    url = input("Enter URL: ").strip()

    # استغلال كل الأنوية تلقائيًا
    cores = os.cpu_count()
    connections = cores * 500  # أقصى ضغط معقول

    print(f"\nDetected Cores  : {cores}")
    print(f"Using Workers   : {connections}")
    print(f"Target URL      : {url}\n")

    async with aiohttp.ClientSession() as session:
        tasks = []

        # تشغيل العمال
        for _ in range(connections):
            tasks.append(asyncio.create_task(worker(session, url)))

        # مراقبة الأداء
        tasks.append(asyncio.create_task(monitor()))

        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
