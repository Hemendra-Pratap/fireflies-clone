import logging
import signal
import sys
import time
from datetime import datetime, timezone
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.job import Job, JobStatus
from app.worker.processor import job_processor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("worker_runner")

running = True


def handle_shutdown(signum, frame):
    global running
    logger.info(f"Received signal {signum}. Shutting down worker runner gracefully...")
    running = False


def poll_and_process_jobs(poll_interval_sec: float = 3.0, worker_id: str = "worker-1"):
    """Main polling loop fetching and executing pending background jobs from database with crash recovery."""
    logger.info(f"Worker runner ({worker_id}) started. Recovering stale jobs and polling...")
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    # Initial stale job recovery on startup
    db_init = SessionLocal()
    try:
        recovered = job_processor.recover_stale_jobs(db_init, stale_timeout_seconds=300)
        if recovered > 0:
            logger.info(f"Recovered {recovered} stale job(s) from previous worker crash.")
    except Exception as init_exc:
        logger.error(f"Error recovering stale jobs on startup: {init_exc}")
    finally:
        db_init.close()

    while running:
        db = SessionLocal()
        try:
            # Periodic stale job recovery
            job_processor.recover_stale_jobs(db, stale_timeout_seconds=300)

            stmt = (
                select(Job)
                .where(Job.status == JobStatus.PENDING)
                .order_by(Job.created_at.asc())
                .limit(1)
            )
            job = db.scalar(stmt)

            if job:
                logger.info(f"Worker {worker_id} executing job ID {job.id} (Type: {job.job_type}, Meeting ID: {job.meeting_id})")
                job_processor.run_job(db, job.id, worker_id=worker_id)
            else:
                time.sleep(poll_interval_sec)
        except Exception as exc:
            logger.error(f"Error in worker runner loop: {exc}")
            time.sleep(poll_interval_sec)
        finally:
            db.close()

    logger.info("Worker runner stopped cleanly.")


if __name__ == "__main__":
    poll_and_process_jobs()
