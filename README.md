## 🔐 SplitBFT Blockchain Simulation

This project simulates a lightweight blockchain consensus mechanism called **SplitBFT**—a modular and scalable BFT protocol suitable for IoT and edge devices. It includes enclave-based transaction validation, quorum voting, and block commit logic across multiple simulated nodes.

---

### 📁 Project Structure

```
fosbft_splitbft/
├── main.py                # Entry point: simulates transactions and node behavior
├── node.py                # Defines Node behavior, ledger, and transaction handling
├── blockchain.py          # Defines Block and Blockchain classes
├── splitbft/
│   ├── enclave.py         # Simulates trusted enclave for validating transactions
│   └── consensus.py       # Handles SplitBFT voting and quorum logic
├── contracts/
│   └── quorum_checker.sol # Optional: Solidity smart contract for quorum validation
├── data/
│   └── ledger.json        # (Optional) Stores committed transactions
└── README.md              # Project documentation
```

---

### 🚀 How It Works

1. **Nodes** propose and validate transactions using a simulated **enclave**.
2. **SplitBFT** logic simulates consensus via quorum-based voting (quorum = 3 of 4 nodes).
3. Transactions with **valid signatures** are processed and committed if quorum is reached.
4. Transactions with **invalid signatures** are rejected and not committed.

---

### 🧠 Key Components

- **`Node`**: Represents a blockchain participant. Can propose, validate, vote, and commit transactions.
- **`SplitBFTConsensus`**: Handles voting and determines when quorum is reached.
- **`Enclave`**: Simulates secure hardware-based validation.
- **`Blockchain`**: Holds committed blocks and a genesis block.
- **Smart Contract (optional)**: Validates if quorum was achieved for a given transaction using Solidity (`quorum_checker.sol`).

---

### 🧪 Running the Simulation

**Requirements**:
- Python 3.x

To simulate 10 transactions with 4 nodes:

```bash
python3 main.py
```

You’ll see logs for:
- Proposer nodes
- Transaction validation (✅ or 🛑)
- Voting from other nodes
- Quorum detection
- Block commit events

---

### ✅ Sample Output

```
>> Node 3 proposing TX tx002
✅ Transaction tx002 passed enclave validation.
Node 3: TX Validated
Node 3 broadcasting vote for TX tx002
Node 3 received vote from Node 1 for TX tx002
Node 3 received vote from Node 2 for TX tx002
✅ Node 3: Quorum reached for TX tx002
🧾 Node 3: Committing TX tx002
```
