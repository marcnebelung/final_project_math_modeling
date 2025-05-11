#!/usr/bin/env python3
"""
Run experiments to evaluate the effect of different parameters of the social force model on 
various metrics of crowd evacuation behavior.
"""
import os
import json
import argparse
import numpy as np
import matplotlib.pyplot as plt
from enhanced_simulation import (
    run_simulation, run_parameter_study, run_scenario, compare_scenarios,
    setup_baseline_scenario, setup_panic_scenario, setup_variable_exit_width_scenario, 
    setup_heterogeneous_crowd
)


def run_desired_speed_study(num_people=50, repetitions=5, base_json_file='input_room.json'):
    """
    Run parameter study on desired speed (vα0).
    - Range: 1.0 m/s (calm) ≤ vα0 ≤ 3.0 m/s (panic)
    - Impact: Higher speeds may trigger the "faster-is-slower" effect due to congestion
    """
    print("\n===== RUNNING DESIRED SPEED PARAMETER STUDY =====")
    
    # Base parameters
    base_params = setup_baseline_scenario(num_people)
    
    # Values to test
    speed_values = [1.0, 1.5, 2.0, 2.5, 3.0]  # m/s
    
    # Run parameter study
    results = run_parameter_study(
        base_params, 
        'desired_speed', 
        speed_values, 
        num_people, 
        repetitions=repetitions,
        base_json_file=base_json_file,
        output_dir='results/desired_speed_study'
    )
    
    return results


def run_repulsion_strength_study(num_people=50, repetitions=5, base_json_file='input_room.json'):
    """
    Run parameter study on repulsion strength (F).
    - Range: 1.0 m²/s² ≤ F ≤ 5.0 m²/s²
    - Impact: Lower values increase collision risk, while higher values cause over-dispersion
    """
    print("\n===== RUNNING REPULSION STRENGTH PARAMETER STUDY =====")
    
    # Base parameters
    base_params = setup_baseline_scenario(num_people)
    
    # Values to test
    repulsion_values = [1.0, 2.0, 3.0, 4.0, 5.0]  # m²/s²
    
    # Run parameter study
    results = run_parameter_study(
        base_params, 
        'F', 
        repulsion_values, 
        num_people, 
        repetitions=repetitions,
        base_json_file=base_json_file,
        output_dir='results/repulsion_strength_study'
    )
    
    return results


def run_relaxation_time_study(num_people=50, repetitions=5, base_json_file='input_room.json'):
    """
    Run parameter study on relaxation time (τα).
    - Range: 0.1 s (agile) ≤ τα ≤ 2.0 s (sluggish)
    - Impact: Shorter times lead to erratic movements, exacerbating congestion
    """
    print("\n===== RUNNING RELAXATION TIME PARAMETER STUDY =====")
    
    # Base parameters
    base_params = setup_baseline_scenario(num_people)
    
    # Values to test
    tau_values = [0.1, 0.5, 1.0, 1.5, 2.0]  # seconds
    
    # Run parameter study
    results = run_parameter_study(
        base_params, 
        'tau', 
        tau_values, 
        num_people, 
        repetitions=repetitions,
        base_json_file=base_json_file,
        output_dir='results/relaxation_time_study'
    )
    
    return results


def run_scenario_comparison(num_people=50, repetitions=5, base_json_file='input_room.json'):
    """
    Run and compare different evacuation scenarios.
    """
    print("\n===== RUNNING SCENARIO COMPARISON =====")
    
    # Create output directory
    output_dir = 'results/scenarios'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    scenario_results = {}
    
    # Scenario 1: Baseline Evacuation
    print("\nRunning Scenario 1: Baseline Evacuation")
    baseline_params = setup_baseline_scenario(num_people)
    baseline_result = run_scenario(
        'baseline', 
        num_people, 
        baseline_params, 
        repetitions=repetitions,
        base_json_file=base_json_file,
        output_dir=output_dir
    )
    if baseline_result:
        scenario_results['Baseline'] = baseline_result
    
    # Scenario 2: Panic-Induced Congestion
    print("\nRunning Scenario 2: Panic-Induced Congestion")
    panic_params = setup_panic_scenario(num_people)
    panic_result = run_scenario(
        'panic', 
        num_people, 
        panic_params, 
        repetitions=repetitions,
        base_json_file=base_json_file,
        output_dir=output_dir
    )
    if panic_result:
        scenario_results['Panic'] = panic_result
    
    # Scenario 3a: Narrow Exit Width
    print("\nRunning Scenario 3a: Narrow Exit Width (0.7m)")
    narrow_params = setup_variable_exit_width_scenario(0.7, num_people)
    narrow_result = run_scenario(
        'narrow_exit', 
        num_people, 
        narrow_params, 
        repetitions=repetitions,
        base_json_file=base_json_file,
        output_dir=output_dir
    )
    if narrow_result:
        scenario_results['Narrow Exit'] = narrow_result
    
    # Scenario 3b: Wide Exit Width
    print("\nRunning Scenario 3b: Wide Exit Width (3.0m)")
    wide_params = setup_variable_exit_width_scenario(3.0, num_people)
    wide_result = run_scenario(
        'wide_exit', 
        num_people, 
        wide_params, 
        repetitions=repetitions,
        base_json_file=base_json_file,
        output_dir=output_dir
    )
    if wide_result:
        scenario_results['Wide Exit'] = wide_result
    
    # Scenario 4: Heterogeneous Crowd
    print("\nRunning Scenario 4: Heterogeneous Crowd")
    hetero_params = setup_heterogeneous_crowd(num_people, fraction_slow=0.2)
    hetero_result = run_scenario(
        'heterogeneous', 
        num_people, 
        hetero_params, 
        repetitions=repetitions,
        base_json_file=base_json_file,
        output_dir=output_dir
    )
    if hetero_result:
        scenario_results['Heterogeneous'] = hetero_result
    
    # Compare all scenarios
    if scenario_results:
        compare_scenarios(
            scenario_results,
            output_dir=f'{output_dir}/comparison'
        )
    
    return scenario_results


def main():
    parser = argparse.ArgumentParser(description='Run evacuation experiments')
    parser.add_argument('--study', type=str, default='all',
                        choices=['all', 'speed', 'repulsion', 'relaxation', 'scenarios'],
                        help='Which parameter study to run')
    parser.add_argument('--people', type=int, default=50,
                        help='Number of people in the simulation')
    parser.add_argument('--repetitions', type=int, default=5,
                        help='Number of repetitions for each parameter set')
    parser.add_argument('--json', type=str, default='input_room.json',
                        help='Input JSON file for simulation configuration')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose output during simulations')

    args = parser.parse_args()

    # Create results directory
    if not os.path.exists('results'):
        os.makedirs('results')

    # Run selected parameter studies
    if args.study in ['all', 'speed']:
        speed_results = run_desired_speed_study(
            num_people=args.people,
            repetitions=args.repetitions,
            base_json_file=args.json
        )
        
    if args.study in ['all', 'repulsion']:
        repulsion_results = run_repulsion_strength_study(
            num_people=args.people,
            repetitions=args.repetitions,
            base_json_file=args.json
        )
        
    if args.study in ['all', 'relaxation']:
        relaxation_results = run_relaxation_time_study(
            num_people=args.people,
            repetitions=args.repetitions,
            base_json_file=args.json
        )
        
    if args.study in ['all', 'scenarios']:
        scenario_results = run_scenario_comparison(
            num_people=args.people,
            repetitions=args.repetitions,
            base_json_file=args.json
        )
    
    print("\nExperiments completed. Results saved in the 'results' directory.")


if __name__ == "__main__":
    main()
