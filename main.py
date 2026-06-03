from __future__ import annotations
import concurrent.futures
import os
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
    required_files = [
        Config.CONFIG_FILE,
        Config.CALENDAR_FILE,
        Config.SHIFTS_FILE,
        Config.PEOPLE_FILE,
    ]
    missing_files = [path for path in required_files if not os.path.exists(path)]
    if missing_files:
        print(f"Error: missing required file(s): {', '.join(missing_files)}")
        return

    params, calendar, people, shifts = IOHandler.load_input()
    print(f"Loaded {len(people)} people, {len(shifts)} shifts.")
    print(f"Parameters: {params}")

    # 2. Run Parallel Simulations
    results = []
    print(f"Running {Config.SA_RUNS} simulations with up to {Config.MAX_WORKERS} workers...")
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
        futures = [
            executor.submit(run_simulation, i, people, shifts, params) 
            for i in range(Config.SA_RUNS)
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
    IOHandler.save_results(top_3, calendar, people, shifts)
    print("--- Done ---")

if __name__ == "__main__":
    main()
