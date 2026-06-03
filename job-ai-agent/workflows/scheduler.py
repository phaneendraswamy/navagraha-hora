from apscheduler.schedulers.asyncio import AsyncIOScheduler


def build_scheduler() -> AsyncIOScheduler:
    """Create the scheduler used by later collection workflows.

    The MVP keeps collection user-triggered to avoid unexpected platform traffic.
    """
    return AsyncIOScheduler(timezone="Asia/Kolkata")

