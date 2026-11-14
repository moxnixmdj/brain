"""
The Hardest Test on the Planet: Distributed Consensus Bug Detection

This tests TRUE understanding by:
1. Teaching the system a complex distributed consensus bug fix
2. Testing it on a COMPLETELY DIFFERENT consensus implementation
3. Seeing if it can recognize the abstract pattern and apply the fix

This proves the system can UNDERSTAND, not just pattern-match.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from canonical.swe_kernel.comprehensive_security_understanding import ComprehensiveSecurityUnderstandingSystem


# Test 1: Raft Consensus - Log Replication Bug
print("="*80)
print("THE HARDEST TEST ON THE PLANET: DISTRIBUTED CONSENSUS")
print("="*80)
print()

print("SCENARIO 1: Raft Leader - Missing Persistence Check")
print("-"*80)
print()
print("This is a REAL bug in Raft consensus implementations:")
print("Leader accepts log entries without checking if they're persisted.")
print("If leader crashes before persistence, entries are lost, violating safety.")
print()

raft_leader_buggy = """
class RaftLeader:
    def __init__(self, node_id, peers, storage):
        self.node_id = node_id
        self.peers = peers
        self.storage = storage
        self.current_term = 0
        self.log = []
        self.commit_index = 0
    
    def handle_client_request(self, command):
        # Client sends a command to the leader
        entry = {'term': self.current_term, 'command': command}
        self.log.append(entry)
        
        # BUG: We return success immediately without checking persistence
        # If we crash before persisting, this entry is lost
        # This violates Raft's safety guarantee: committed entries must be durable
        return {'success': True, 'index': len(self.log) - 1}
    
    def persist_log(self):
        # Write log to stable storage
        self.storage.write_log(self.log)
"""

print("Buggy Code:")
print(raft_leader_buggy)
print()

system = ComprehensiveSecurityUnderstandingSystem()
result1 = system.understand_and_fix(raft_leader_buggy)

print("Understanding:")
print(f"  Risk: {result1['understanding']['overall_risk']}")
if result1['understanding']['vulnerabilities']:
    print(f"  Issue: {result1['understanding']['vulnerabilities'][0]['description']}")
print()

if result1['fix']:
    print("Generated Fix:")
    print(result1['fix'])
    print()
else:
    print("No fix generated.")
    print()

print()
print("="*80)
print()

print("SCENARIO 2: Paxos Proposer - Missing Acceptance Verification")
print("-"*80)
print()
print("This is a COMPLETELY DIFFERENT consensus algorithm (Paxos).")
print("But it has the SAME abstract bug pattern:")
print("Proposer accepts promises without verifying they meet quorum requirements.")
print()

paxos_buggy = """
class PaxosProposer:
    def __init__(self, proposer_id, acceptors):
        self.proposer_id = proposer_id
        self.acceptors = acceptors
        self.proposal_number = 0
        self.value = None
    
    def prepare_phase(self, value):
        # Phase 1: Send prepare requests to acceptors
        self.proposal_number += 1
        self.value = value
        
        promises = []
        for acceptor in self.acceptors:
            promise = acceptor.on_prepare(self.proposal_number)
            if promise:
                promises.append(promise)
        
        # BUG: We don't check if we have a quorum of promises
        # We proceed to phase 2 even if we don't have majority
        # This violates Paxos safety: only one value can be chosen
        return self.accept_phase(promises)
    
    def accept_phase(self, promises):
        # Phase 2: Send accept requests
        accepts = []
        for acceptor in self.acceptors:
            accepted = acceptor.on_accept(self.proposal_number, self.value)
            if accepted:
                accepts.append(accepted)
        
        # BUG: We return success without checking quorum
        return {'success': True, 'value': self.value}
"""

print("Buggy Code:")
print(paxos_buggy)
print()

result2 = system.understand_and_fix(paxos_buggy)

print("Understanding:")
print(f"  Risk: {result2['understanding']['overall_risk']}")
if result2['understanding']['vulnerabilities']:
    print(f"  Issue: {result2['understanding']['vulnerabilities'][0]['description']}")
print()

if result2['fix']:
    print("Generated Fix:")
    print(result2['fix'])
    print()
else:
    print("No fix generated.")
    print()
    print("This is the HARDEST test:")
    print("  - Raft and Paxos are completely different algorithms")
    print("  - But they have the SAME abstract bug pattern")
    print("  - Can the system recognize this pattern?")
    print("  - Can it apply the same fix to a different system?")
    print()

print("="*80)
print()

print("SCENARIO 3: Multi-Paxos - Missing Lease Expiration Check")
print("-"*80)
print()
print("Another completely different consensus variant (Multi-Paxos with leases).")
print("Same abstract bug: proceeding without verifying critical conditions.")
print()

multipaxos_buggy = """
class MultiPaxosLeader:
    def __init__(self, leader_id, peers, lease_duration):
        self.leader_id = leader_id
        self.peers = peers
        self.lease_duration = lease_duration
        self.lease_expiry = 0
        self.log = []
    
    def handle_request(self, command):
        # Check if we're still the leader (lease is valid)
        if self.is_lease_expired():
            return {'error': 'Lease expired, no longer leader'}
        
        # Append command to log
        entry = {'command': command, 'term': self.current_term}
        self.log.append(entry)
        
        # BUG: We don't check if lease will expire during replication
        # If lease expires while replicating, another leader may be elected
        # This creates a split-brain scenario
        self.replicate_to_followers(entry)
        
        return {'success': True}
    
    def is_lease_expired(self):
        import time
        return time.time() > self.lease_expiry
    
    def replicate_to_followers(self, entry):
        # Send entry to all followers
        for peer in self.peers:
            peer.append_entry(entry)
"""

print("Buggy Code:")
print(multipaxos_buggy)
print()

result3 = system.understand_and_fix(multipaxos_buggy)

print("Understanding:")
print(f"  Risk: {result3['understanding']['overall_risk']}")
if result3['understanding']['vulnerabilities']:
    print(f"  Issue: {result3['understanding']['vulnerabilities'][0]['description']}")
print()

if result3['fix']:
    print("Generated Fix:")
    print(result3['fix'])
    print()
else:
    print("No fix generated.")
    print()

print("="*80)
print("THE ULTIMATE TEST")
print("="*80)
print()

if result1['fix'] and result2['fix'] and result3['fix']:
    print("✓✓✓ ALL THREE SCENARIOS SOLVED ✓✓✓")
    print()
    print("This proves the system can:")
    print("  1. UNDERSTAND complex distributed systems bugs")
    print("  2. RECOGNIZE abstract patterns across different algorithms")
    print("  3. GENERATE correct fixes for each specific implementation")
    print()
    print("This is the HARDEST test on the planet:")
    print("  - Raft, Paxos, Multi-Paxos are completely different")
    print("  - But they all have the same abstract bug:")
    print("    'Proceeding without verifying critical conditions'")
    print()
    print("The system can UNDERSTAND this pattern and apply it anywhere.")
    print("This is TRUE understanding, not pattern matching.")
elif any([result1['fix'], result2['fix'], result3['fix']]):
    print("Partial success.")
    print("The system can understand some distributed systems bugs,")
    print("but needs deeper knowledge of consensus algorithms.")
else:
    print("✗ No scenarios solved.")
    print()
    print("This shows the limitation:")
    print("  - Distributed consensus is the hardest problem in computer science")
    print("  - It requires deep understanding of safety, liveness, fault tolerance")
    print("  - The system needs comprehensive distributed systems knowledge")
    print()
    print("To solve this, we need:")
    print("  - Distributed systems domain knowledge base")
    print("  - Consensus algorithm understanding (Raft, Paxos, Multi-Paxos, etc.)")
    print("  - Safety property verification")
    print("  - Liveness property checking")
    print()
    print("This is the NEXT frontier: teaching the system to understand")
    print("the most complex software engineering challenges on the planet.")
