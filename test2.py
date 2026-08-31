import asyncio


async def main():

    async def task1():
        await asyncio.sleep(10)
        return "Task1 is completed"

    async def task2():
        await asyncio.sleep(5)
        return "Task2 is completed"

    async def task3():
        return "Task3 is completed"

    tasks = [
        asyncio.create_task(task1()),
        asyncio.create_task(task2()),
        asyncio.create_task(task3())
    ]

    for task in asyncio.as_completed(tasks):
        result = await task
        print(result)


asyncio.run(main())