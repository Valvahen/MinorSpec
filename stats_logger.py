# stats_logger.py
import time

class StatsLogger:
    def __init__(self):
        self.start_time = time.time()
        self.message_count = 0
        self.blocks_finalized = 0
        self.transactions_processed = 0

    def log_message(self,count=1):
        self.message_count += 1

    def log_block(self, block=None):
        self.blocks_finalized += 1
        if block:
            print(f"[StatsLogger] Block finalized with proof: {block.get('proof')}")

    def log_transactions(self, tx_count):
        self.transactions_processed += tx_count

    def summary(self):
        elapsed = time.time() - self.start_time
        return {
            'TimeElapsed_sec': round(elapsed, 2),
            'BlocksFinalized': self.blocks_finalized,
            'Messages': self.message_count,
            'TransactionsProcessed': self.transactions_processed,
            'TPS': round(self.transactions_processed / elapsed, 2) if elapsed else 0
        }

# Global instance (importable anywhere)
logger = StatsLogger()
