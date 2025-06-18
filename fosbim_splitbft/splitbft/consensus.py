class SplitBFTConsensus:
    def __init__(self, node):
        self.node = node
        self.votes = {}  # votes[tx_id] = set of voter IDs

    def broadcast_vote(self, tx):
        print(f"Node {self.node.id} broadcasting vote for TX {tx['id']}")
        # Simulate sending votes to other nodes
        for i in range(1, 5):  # Simulate 4 total nodes
            if i != self.node.id:
                self.receive_vote(tx, i)

        # Node votes for its own tx as well
        self.receive_vote(tx, self.node.id)

    def receive_vote(self, tx, from_id):
        tx_id = tx["id"]
        if tx_id not in self.votes:
            self.votes[tx_id] = set()
        self.votes[tx_id].add(from_id)

        print(f"Node {self.node.id} received vote from Node {from_id} for TX {tx_id}")

        if len(self.votes[tx_id]) >= 3:  # quorum = 3 of 4
            print(f"✅ Node {self.node.id}: Quorum reached for TX {tx_id}")
            self.node.vote_commit(tx)