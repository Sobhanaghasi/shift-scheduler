from __future__ import annotations
import concurrent.futures
from config import Config
from io_handler import IOHandler
from cost_engine import CostEngine
from scheduler import Scheduler
from domain import Shift

def run_simulation(seed, people, shifts, params):
    """Wrapper for parallel execution"""
    # Re-create engine/scheduler per thread to avoid shared state issues
    shift_map = {s.id: s for s in shifts}
    engine = CostEngine(shift_map, params)
    solver = Scheduler(people, shifts, engine)
    return solver.solve(seed)

def main():
    print("--- Custom AI Scheduler Starting ---")
    
    # 1. Load Data
    input_file = "input.json"
    if not os.path.exists(input_file):
        print(f"Error: {input_file} missing.")
        return

    params, people, shifts = IOHandler.load_input(input_file)
    print(f"Loaded {len(people)} people, {len(shifts)} shifts.")
    print(f"Parameters: {params}")

    # 2. Run Parallel Simulations
    results = []
    print(f"Running {Config.MAX_WORKERS} simulations in parallel...")
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
        futures = [
            executor.submit(run_simulation, i, people, shifts, params) 
            for i in range(10)
        ]
        
        for future in concurrent.futures.as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                print(f"Simulation failed: {e}")

    # 3. Sort by Energy (Ascending = Lower Cost is Better)
    results.sort(key=lambda x: x.energy)
    
    # 4. Save Top 3
    top_3 = results[:3]
    IOHandler.save_results(top_3)
    print("--- Done ---")

if __name__ == "__main__":
    import os
    main()