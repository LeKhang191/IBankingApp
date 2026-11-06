"""Background worker for Saga recovery and transactional outbox delivery."""

import asyncio
import logging

from app.main import (
    OUTBOX_POLL_SECONDS,
    list_recoverable_sagas,
    process_outbox_once,
    process_saga,
)

logger = logging.getLogger("ibanking.payment.worker")


async def run_forever():
    logger.info("Payment worker started: Saga recovery + transactional outbox")
    while True:
        try:
            for transaction_id in list_recoverable_sagas(limit=50):
                try:
                    result = await process_saga(transaction_id)
                    logger.info(
                        "Saga recovery checked transaction_id=%s status=%s",
                        transaction_id,
                        result.get("status") if result else "missing",
                    )
                except Exception:
                    logger.exception("Saga recovery failed transaction_id=%s", transaction_id)

            # Drain a small batch per loop; SKIP LOCKED supports multiple workers.
            for _ in range(20):
                delivered_or_retried = await process_outbox_once()
                if not delivered_or_retried:
                    break
        except Exception:
            logger.exception("Payment worker loop failed")

        await asyncio.sleep(OUTBOX_POLL_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(
        level="INFO",
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    asyncio.run(run_forever())
