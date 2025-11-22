"""Performance benchmarks for critical functions."""

import time
from app.core.engine import Predictor
from app.core.roadmap import generate_roadmaps


def benchmark_predictor():
    """Benchmark prediction speed."""
    predictor = Predictor()
    
    # Add sample history
    for _ in range(100):
        predictor.add("B" if _ % 2 == 0 else "P")
    
    start = time.perf_counter()
    for _ in range(1000):
        predictor.predict()
    elapsed = time.perf_counter() - start
    
    print(f"Predictor: {elapsed:.4f}s for 1000 predictions ({elapsed/1000*1000:.2f}ms per prediction)")


def benchmark_roadmap():
    """Benchmark roadmap generation."""
    history = "".join(["B" if i % 2 == 0 else "P" for i in range(200)])
    
    start = time.perf_counter()
    for _ in range(100):
        generate_roadmaps(history)
    elapsed = time.perf_counter() - start
    
    print(f"Roadmap: {elapsed:.4f}s for 100 generations ({elapsed/100*1000:.2f}ms per generation)")


if __name__ == "__main__":
    print("🏃 Running performance benchmarks...\n")
    benchmark_predictor()
    benchmark_roadmap()

