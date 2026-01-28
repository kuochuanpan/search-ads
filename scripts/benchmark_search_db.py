import time
import sys
import os
from statistics import mean

# Add src to path
sys.path.append(os.getcwd())

from src.db.repository import PaperRepository, NoteRepository

def benchmark():
    print("Initializing repositories...")
    repo = PaperRepository()
    note_repo = NoteRepository()
    
    # Get all bibcodes first to have a sample set
    print("Fetching all bibcodes...")
    all_papers = repo.get_all(limit=1000)
    bibcodes = [p.bibcode for p in all_papers]
    count = len(bibcodes)
    
    if count == 0:
        print("No papers in database to benchmark. Please add some papers first.")
        return

    print(f"Benchmarking with {count} papers/bibcodes.\n")

    # --- Scenario 1: Fetching Papers ---
    print("--- Benchmark 1: Fetching Papers ---")
    
    # Old way: Iterative
    start_time = time.time()
    for bibcode in bibcodes:
        repo.get(bibcode)
    iterative_time = time.time() - start_time
    print(f"Iterative Fetching (Old Way): {iterative_time:.4f} seconds")
    
    # New way: Batch
    start_time = time.time()
    repo.get_batch(bibcodes)
    batch_time = time.time() - start_time
    print(f"Batch Fetching (New Way):     {batch_time:.4f} seconds")
    
    if batch_time > 0:
        speedup = iterative_time / batch_time
        print(f"Speedup: {speedup:.2f}x")
    print("")

    # --- Scenario 2: Fetching Notes ---
    print("--- Benchmark 2: Fetching Notes ---")
    
    # Old way: Iterative
    start_time = time.time()
    for bibcode in bibcodes:
        note_repo.get(bibcode)
    iterative_note_time = time.time() - start_time
    print(f"Iterative Fetching (Old Way): {iterative_note_time:.4f} seconds")
    
    # New way: Batch
    start_time = time.time()
    note_repo.get_batch(bibcodes)
    batch_note_time = time.time() - start_time
    print(f"Batch Fetching (New Way):     {batch_note_time:.4f} seconds")
    
    if batch_note_time > 0:
        note_speedup = iterative_note_time / batch_note_time
        print(f"Speedup: {note_speedup:.2f}x")
    print("")
    
    # --- Conclusion ---
    total_iterative = iterative_time + iterative_note_time
    total_batch = batch_time + batch_note_time
    print("--- Total Impact on Search/Re-ranking ---")
    print(f"Total Iterative Time: {total_iterative:.4f} seconds")
    print(f"Total Batch Time:     {total_batch:.4f} seconds")
    if total_batch > 0:
        total_speedup = total_iterative / total_batch
        print(f"Total Database Speedup: {total_speedup:.2f}x")

if __name__ == "__main__":
    benchmark()
