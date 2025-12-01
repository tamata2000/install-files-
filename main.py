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

    # طلب الرابط
    url = input("Enter URL: ").strip()

    # عرض عدد الأنوية
    cores = os.cpu_count()
    print(f"Detected CPU Cores: {cores}")

    # طلب عدد الثريدات من المستخدم
    try:
        connections = 3000
    except:
        print("Invalid input, using default = 500")
        connections = 500

    print(f"\nUsing Workers   : {connections}")
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
