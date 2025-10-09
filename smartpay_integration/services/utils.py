from django.core.cache import cache


def acquire_locks(transaction_id, resource_id, amount, transaction_type):
    """Acquire both transaction and meter locks"""
    txn_lock = f"txn_{transaction_id}"
    resource_lock = f"resource_{resource_id}_{amount}_{transaction_type}"
    
    # Try transaction lock first
    if not cache.add(txn_lock, 'locked', 30):
        return None, "Transaction already being processed"
    
    # Try resource lock second
    if not cache.add(resource_lock, 'locked', 30):
        cache.delete(txn_lock)  # Cleanup
        return None, f"{'Meter' if transaction_type == 'sell_power' else 'Bill'} transaction in progress"
    
    return [txn_lock, resource_lock], None

def release_locks(lock_keys):
    """Release all acquired locks"""
    if lock_keys:
        for lock_key in lock_keys:
            cache.delete(lock_key)