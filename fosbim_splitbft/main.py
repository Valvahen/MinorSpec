from node import Node
import time
import random

# Create 4 nodes
nodes = [Node(i) for i in range(1, 5)]

# Simulate 10 transactions from random nodes
for i in range(10):
    is_valid = random.choice([True, True, True, False])  # ~75% valid
    signature = "valid_signature" if is_valid else "invalid_signature"
    
    tx = {
        "id": f"tx{i:03}",
        "data": f"send {i+1} coins",
        "signature": signature
    }

    proposer = random.choice(nodes)
    proposer.receive_transaction(tx)

    time.sleep(1.5)  # Simulate network delay
