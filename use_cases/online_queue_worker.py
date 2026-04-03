from use_cases.process_signal import process_online_job


async def online_worker(request_queue, repository, trademo_client):
    print("[QUEUE] Worker запущен, жду задачи...")

    while True:
        job = await request_queue.get()
        try:
            await process_online_job(job, repository, trademo_client)
        except Exception as e:
            print(f"[QUEUE] Ошибка обработки задачи: {e}")
        finally:
            request_queue.task_done()
