def validate_transaction(tx):
    if tx.get("signature") != "valid_signature":
        print(f"🛑 Transaction {tx['id']} has invalid signature. Rejected.")
        return False
    print(f"✅ Transaction {tx['id']} passed enclave validation.")
    return True
