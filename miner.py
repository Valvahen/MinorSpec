import blockchain
import time
import new_consensus_module
import output
import encryption_module
import modification
import random


class Miner:
    def __init__(self, address, trans_delay, gossiping):
        self.address = "Miner_" + str(address)
        self.priority = random.randint(1, 5)
        self.top_block = {}
        self.isAuthorized = False
        self.next_pos_block_from = self.address
        self.neighbours = set()
        self.trans_delay = trans_delay/1000
        self.gossiping = gossiping
        self.waiting_times = {}
        self.dpos_vote_for = None
        self.amount_to_be_staked = None
        self.delegates = None
        self.adversary = False
        self.local_mempool = []

    def build_block(self, num_of_tx_per_block, miner_list, type_of_consensus, blockchain_function, expected_chain_length, AI_assisted_mining_wanted,splitbft_mode=0):
        # 1. Authority Check (PoA)
        if type_of_consensus == 3 and not self.isAuthorized:
            output.unauthorized_miner_msg(self.address)
            return # Stop execution for unauthorized miners

        # 2. Timing Check (PoET)
        elif type_of_consensus == 4:
            waiting_time = (self.top_block['Body']['timestamp'] + self.waiting_times[self.top_block['Header']['blockNo'] + 1]) - time.time()
            if waiting_time <= 0:
                self.continue_building_block(num_of_tx_per_block, miner_list, type_of_consensus, blockchain_function, expected_chain_length, AI_assisted_mining_wanted)

        # 3. YOUR NOVELTY: SplitBFT Check
        elif type_of_consensus == 6:
            # Step 1: Generate the proposal
            proposal_block = self.generate_splitbft_proposal(num_of_tx_per_block, miner_list, blockchain_function, splitbft_mode)
            
            if proposal_block:
                # Step 2: Trigger the Voting Phase based on your 4 modes
                # This is where your novelty "executes"
                self.execute_splitbft_consensus(proposal_block, miner_list, splitbft_mode, blockchain_function, expected_chain_length)

        else:
            self.continue_building_block(num_of_tx_per_block, miner_list, type_of_consensus, blockchain_function, expected_chain_length, False)

    def generate_splitbft_proposal(self, num_of_tx_per_block, miner_list, blockchain_function, splitbft_mode):
            accumulated_transactions = new_consensus_module.accumulate_transactions(num_of_tx_per_block, self.local_mempool, blockchain_function, self.address)
            if accumulated_transactions:
                # We use abstract_block_building but we DON'T broadcast yet
                return self.abstract_block_building(blockchain_function, accumulated_transactions, miner_list, 6, False)
            return None   

    def execute_splitbft_consensus(self, proposal_block, miner_list, mode, blockchain_function, expected_chain_length):
        # 1. We extract the votes already collected in SplitBFT_proof
        # If signatures exist, use that count. Otherwise, default to 0.
        votes = len(proposal_block.get('signatures', []))
        
        # 2. Determine the required quorum based on the mode
        # We match these to the logic you wrote in new_consensus_module.py
        total_nodes = len(miner_list)
        
        if mode == 0:
            required_quorum = 3 # Matches your 'Standard' mode setting
        elif mode == 1:
            required_quorum = proposal_block.get('target_quorum', (total_nodes // 2) + 1)
        elif mode == 2:
            # Hierarchical: the proof module already filtered the voters
            required_quorum = votes 
        elif mode == 3:
            # Priority: the proof module already filtered high-priority signers
            required_quorum = votes
        else:
            required_quorum = total_nodes # Fallback safety

        # 3. Simulate network delay (optional, keeps the simulation realistic)
        # We loop through the signatures collected to simulate their arrival
        for _ in range(votes):
            time.sleep(self.trans_delay)

        # 4. FINAL CHECK
        # If the number of signatures we collected meets the requirement
        if votes >= required_quorum and votes > 0:
            print(f"Quorum reached for Mode {mode}! Finalizing block.")
            
            # Broadcast the finalized block to the entire network
            for elem in miner_list:
                elem.receive_new_block(
                    proposal_block, 
                    6, 
                    miner_list, 
                    blockchain_function, 
                    expected_chain_length
                )
        else:
            print(f"FAILED: Quorum not reached for Mode {mode}. Votes: {votes}/{required_quorum}")

    def continue_building_block(self, num_of_tx_per_block, miner_list, type_of_consensus, blockchain_function, expected_chain_length, AI_assisted_mining_wanted):
        accumulated_transactions = new_consensus_module.accumulate_transactions(num_of_tx_per_block, self.local_mempool, blockchain_function,
                                                                                self.address)
        if accumulated_transactions:
            transactions = accumulated_transactions
            new_block = self.abstract_block_building(blockchain_function, transactions, miner_list, type_of_consensus, AI_assisted_mining_wanted)
            output.block_info(new_block, type_of_consensus)
            for tx in transactions:
                try:
                    self.local_mempool.remove(tx)
                except Exception as e:
                    pass
            time.sleep(self.trans_delay)
            for elem in miner_list:
                if elem.address in self.neighbours:
                    elem.receive_new_block(new_block, type_of_consensus, miner_list, blockchain_function,
                                           expected_chain_length)

    def abstract_block_building(self, blockchain_function, transactions, miner_list, type_of_consensus, AI_assisted_mining_wanted,splitbft_mode=0):
        if blockchain_function == 3:
            transactions = self.validate_transactions(transactions, "generator")
        if self.gossiping:
            self.gossip(blockchain_function, miner_list)
        new_block = new_consensus_module.generate_new_block(transactions, self.address,
                                                            self.top_block['Header']['hash'], type_of_consensus,
                                                            AI_assisted_mining_wanted, self.adversary,splitbft_mode=splitbft_mode,miner_list=miner_list)
        if type_of_consensus == 4:
            new_block['Header']['PoET'] = encryption_module.retrieve_signature_from_saved_key(
                new_block['Body']['previous_hash'], self.address)
        return new_block

    def receive_new_block(self, new_block, type_of_consensus, miner_list, blockchain_function, expected_chain_length):
        block_already_received = False
        local_chain_temporary_file = modification.read_file(str("temporary/" + self.address + "_local_chain.json"))
        # print("a new block is received from " + str(new_block['generator_id']))
        condition_1 = (len(local_chain_temporary_file) == 0) and (new_block['Header']['generator_id'] == 'The Network')
        if condition_1:
            self.add(new_block, blockchain_function, expected_chain_length, miner_list)
        else:
            if self.gossiping:
                self.gossip(blockchain_function, miner_list)
            list_of_hashes_in_local_chain = []
            for key in local_chain_temporary_file:
                read_hash = local_chain_temporary_file[key]['Header']['hash']
                list_of_hashes_in_local_chain.append(read_hash)
                if new_block['Header']['hash'] == read_hash:
                    block_already_received = True
                    break
            if not block_already_received:
                if new_consensus_module.block_is_valid(type_of_consensus, new_block, self.top_block, self.next_pos_block_from, miner_list, self.delegates):
                    self.add(new_block, blockchain_function, expected_chain_length, miner_list)
                    time.sleep(self.trans_delay)
                    for tx in new_block["Body"]["transactions"]:
                        try:
                            self.local_mempool.remove(tx)
                        except Exception as e:
                            pass
                    for elem in miner_list:
                        if elem.address in self.neighbours:
                            elem.receive_new_block(new_block, type_of_consensus, miner_list, blockchain_function, expected_chain_length)

    def validate_transactions(self, list_of_new_transactions, miner_role):
        user_wallets_temporary_file = modification.read_file(str("temporary/" + self.address + "_users_wallets.json"))
        if list_of_new_transactions:
            for key in user_wallets_temporary_file:
                for transaction in list_of_new_transactions:
                    if miner_role == "receiver":
                        if key == (str(transaction[1]) + "." + str(transaction[2])):
                            if user_wallets_temporary_file[key]['wallet_value'] >= transaction[0]:
                                user_wallets_temporary_file[key]['wallet_value'] -= transaction[0]
                            else:
                                return False
                        if key == (str(transaction[3]) + "." + str(transaction[4])):
                            user_wallets_temporary_file[key]['wallet_value'] += transaction[0]
                    if miner_role == "generator" and key == (str(transaction[1]) + "." + str(transaction[2])):
                        if user_wallets_temporary_file[key]['wallet_value'] < transaction[0]:
                            output.illegal_tx(transaction, user_wallets_temporary_file[key]['wallet_value'])
                            del transaction
        if miner_role == "generator":
            return list_of_new_transactions
        if miner_role == "receiver":
            modification.rewrite_file(str("temporary/" + self.address + "_users_wallets.json"), user_wallets_temporary_file)
            return True

    def add(self, block, blockchain_function, expected_chain_length, list_of_miners):
        ready = False
        local_chain_temporary_file = modification.read_file("temporary/" + self.address + "_local_chain.json")
        if len(local_chain_temporary_file) == 0:
            ready = True
        else:
            condition = blockchain_function == 3 and self.validate_transactions(block['Body']['transactions'], "receiver")
            if blockchain_function != 3 or condition:
                if block['Body']['previous_hash'] == self.top_block['Header']['hash']:
                    blockchain.report_a_successful_block_addition(block['Header']['generator_id'], block['Header']['hash'])
                    # output.block_success_addition(self.address, block['generator_id'])
                    ready = True
        if ready:
            block['Header']['blockNo'] = len(local_chain_temporary_file)
            self.top_block = block
            local_chain_temporary_file[str(len(local_chain_temporary_file))] = block
            modification.rewrite_file(str("temporary/" + self.address + "_local_chain.json"), local_chain_temporary_file)
            self.remove_confirmed_txs_from_local_mempool(block)
            if self.gossiping:
                self.update_global_longest_chain(local_chain_temporary_file, blockchain_function, list_of_miners)

    def remove_confirmed_txs_from_local_mempool(self, confirmed_bock):
        if confirmed_bock["Header"]["generator_id"] != "The Network":
            try:
                for tx in confirmed_bock["Body"]["transactions"]:
                    self.local_mempool.remove(tx)
            except Exception as e:
                pass

    def gossip(self, blockchain_function, list_of_miners):
        local_chain_temporary_file = modification.read_file(str("temporary/" + self.address + "_local_chain.json"))
        temporary_global_longest_chain = modification.read_file('temporary/longest_chain.json')
        condition_1 = len(temporary_global_longest_chain['chain']) > len(local_chain_temporary_file)
        condition_2 = self.global_chain_is_confirmed_by_majority(temporary_global_longest_chain['chain'], len(list_of_miners))
        if condition_1 and condition_2:
            confirmed_chain = temporary_global_longest_chain['chain']
            confirmed_chain_from = temporary_global_longest_chain['from']
            modification.rewrite_file(str("temporary/" + self.address + "_local_chain.json"), confirmed_chain)
            self.top_block = confirmed_chain[str(len(confirmed_chain) - 1)]
            output.local_chain_is_updated(self.address, len(confirmed_chain))
            if blockchain_function == 3:
                user_wallets_temp_file = modification.read_file(str("temporary/" + confirmed_chain_from + "_users_wallets.json"))
                modification.rewrite_file(str("temporary/" + self.address + "_users_wallets.json"), user_wallets_temp_file)

    def global_chain_is_confirmed_by_majority(self, global_chain, no_of_miners):
        chain_is_confirmed = True
        temporary_confirmations_log = modification.read_file('temporary/confirmation_log.json')
        for block in global_chain:
            condition_0 = block != '0'
            if condition_0:
                condition_1 = not (global_chain[block]['Header']['hash'] in temporary_confirmations_log)
                if condition_1:
                    chain_is_confirmed = False
                    break
                else:
                    condition_2 = temporary_confirmations_log[global_chain[block]['Header']['hash']]['votes'] <= (no_of_miners / 2)
                    if condition_2:
                        chain_is_confirmed = False
                        break
        return chain_is_confirmed

    def update_global_longest_chain(self, local_chain_temporary_file, blockchain_function, list_of_miners):
        temporary_global_longest_chain = modification.read_file('temporary/longest_chain.json')
        if len(temporary_global_longest_chain['chain']) < len(local_chain_temporary_file):
            temporary_global_longest_chain['chain'] = local_chain_temporary_file
            temporary_global_longest_chain['from'] = self.address
            modification.rewrite_file('temporary/longest_chain.json', temporary_global_longest_chain)
        else:
            if len(temporary_global_longest_chain['chain']) > len(local_chain_temporary_file) and self.gossiping:
                self.gossip(blockchain_function, list_of_miners)
    
    def sign_block(self, block):
        """
        Simulates the miner verifying the block and providing a signature.
        """
        # This print statement confirms the miner is actively participating
        print(f"   [CONSENSUS] {self.address} is validating and signing block...")
        
        # In a real system, you would return a cryptographic signature here
        return f"Sig-from-{self.address}"
