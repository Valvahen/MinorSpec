from splitbft.enclave import validate_transaction
from splitbft.consensus import SplitBFTConsensus

class Node:
    def __init__(self, id):
        self.id = id
        self.consensus = SplitBFTConsensus(self)
        self.ledger = []

    def receive_transaction(self, tx):
        print(f"\n>> Node {self.id} proposing TX {tx['id']}")
        if validate_transaction(tx):
            print(f"Node {self.id}: TX Validated")
            self.consensus.broadcast_vote(tx)
        else:
            print(f"Node {self.id}: TX {tx['id']} failed validation.")

    def vote_commit(self, tx):
        print(f"🧾 Node {self.id}: Committing TX {tx['id']}")
        self.ledger.append(tx)
