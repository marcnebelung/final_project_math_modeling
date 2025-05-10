#!/usr/bin/env python3
"""
Run the evacuation time analysis with different population sizes.
Simple version for basic scenario with one domain, one destination, and one sensor.
"""
from evacuation_simulation import run_multiple_simulations, plot_evacuation_results
import json
import argparse


def main():
    parser = argparse.ArgumentParser(description='Run evacuation time analysis')
    parser.add_argument('--populations', type=str, default='10,25,50,75,100,150',
                        help='Comma-separated list of population sizes to test')
    parser.add_argument('--repetitions', type=int, default=5,
                        help='Number of repetitions for each population size')
    parser.add_argument('--json', type=str, default='input_room.json',
                        help='Input JSON file for simulation configuration')
    parser.add_argument('--output', type=str, default='evacuation_results.json',
                        help='Output file for saving results')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose output during simulations')

    args = parser.parse_args()

    # Parse population sizes
    population_sizes = [int(n) for n in args.populations.split(',')]

    print(f"Running analysis with population sizes: {population_sizes}")
    print(f"Each size will be simulated {args.repetitions} times")

    # Run simulations
    results = run_multiple_simulations(
        population_sizes,
        repetitions=args.repetitions,
        base_json_file=args.json
    )

    # Save results to file
    with open(args.output, 'w') as f:
        # Convert keys to strings for JSON serialization
        json_results = {str(k): v for k, v in results.items()}
        json.dump(json_results, f, indent=2)

    print(f"\nResults saved to {args.output}")

    # Plot results
    coeffs = plot_evacuation_results(results)

    # Print summary
    print("\nResults summary:")
    print("---------------")
    for n in sorted(results.keys()):
        print(f"Population {n}: {results[n]['mean']:.2f} ± {results[n]['std']:.2f} seconds")

    print(f"\nTrend equation: {coeffs[0]:.4f}x² + {coeffs[1]:.2f}x + {coeffs[2]:.2f}")
    print("\nPlot saved as 'evacuation_results.png'")


if __name__ == "__main__":
    main()
