import os
import json
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from cromosim.domain import Domain
from cromosim.domain import Destination
from cromosim.micro import people_initialization, compute_contacts
from cromosim.micro import compute_forces, move_people, people_update_destination

def create_domain(door_width=5):
    """
    Create domain with specified door width, following the approach in domain_design.py
    """
    # Create domain
    dom = Domain(name='room', background='../domain_testing/room_3_walls.png', pixel_size=0.1)

    # Define colors
    wall_color = [0, 0, 0]
    door_color = [255, 0, 0]

    # Define room dimensions
    bottom_xs = (3, 37)  # X-coordinates of bottom wall
    room_width = bottom_xs[1] - bottom_xs[0]
    center = bottom_xs[0] + room_width/2

    # Calculate door position based on door width
    door_start = center - door_width/2
    door_end = center + door_width/2

    # Create bottom walls with door opening
    left_bottom_wall = Line2D((bottom_xs[0], door_start), (3, 3), linewidth=2)
    dom.add_shape(left_bottom_wall, outline_color=wall_color, fill_color=wall_color)

    right_bottom_wall = Line2D((door_end, bottom_xs[1]), (3, 3), linewidth=2)
    dom.add_shape(right_bottom_wall, outline_color=wall_color, fill_color=wall_color)

    # Add exit destination
    dest_line = Line2D([bottom_xs[0]-2, bottom_xs[1]+2], [2, 2], linewidth=2)
    dom.add_shape(dest_line, outline_color=door_color, fill_color=door_color)

    # Build the domain
    dom.build_domain()

    # Create destination object
    dest = Destination(name='door', colors=[door_color], excluded_colors=[wall_color])
    dom.add_destination(dest)

    return dom

def create_sensor(domain):
    """
    Create sensor across the entire bottom of the room to measure flow
    """
    # Create sensor just inside the exit
    sensor = {
        "name": "exit_sensor",
        "line": [3, 3, 37, 3],  # positioned just below the exit
        "id": [],
        "times": [],
        "xy": [],
        "dir": []
    }

    return sensor

def run_simulation(
    num_people=50,
    desired_speed=1.2,
    repulsion_strength=2000.0,
    relaxation_time=0.5,
    door_width=5,
    seed=40,
    Tf=500.0,
    dt=0.005,
    verbose=False
):
    """
    Run a single simulation with the specified parameters.
    Returns dict with metrics results.
    """
    # Create domain with specified door width
    dom = create_domain(door_width)
    domain_name = dom.name

    # Create sensor
    sensor = create_sensor(dom)
    all_sensors = {domain_name: [sensor]}

    # Define other simulation parameters
    mass = 80.0
    kappa = 120000.0
    delta = 0.08
    lambda_ = 0.5
    eta = 240000.0
    projection_method = "cvxopt"
    dmax = 0.1
    dmin_people = 0.0
    dmin_walls = 0.0

    # Initialize simulation time
    t = 0.0

    # Create output directory if it doesn't exist
    prefix = "results/"
    if not os.path.exists(prefix):
        os.makedirs(prefix)

    # Set up metrics tracking
    metrics = {
        "evacuation_time": 0,
        "flow_rate": [],  # Will track people/second
        "collision_count": [],  # Track collisions over time
        "exit_density": []  # Track density near exit over time
    }

    # Define exit area for density calculation (rectangle around door)
    center_x = 20  # Assuming center is at x=20
    exit_area_width = door_width + 2  # Exit width plus margin
    exit_area = {
        "x_min": center_x - exit_area_width/2,
        "x_max": center_x + exit_area_width/2,
        "y_min": 2.5,  # Just below the exit
        "y_max": 5.5   # Extend a few meters into the room
    }
    exit_area_size = exit_area_width * (exit_area["y_max"] - exit_area["y_min"])  # Area size in m²

    # Time tracking for computing metrics
    last_metric_time = 0
    metric_interval = 1.0  # Calculate metrics every second

    # Initialize people
    groups = [{
        "nb": num_people,
        "radius_distribution": ["uniform", 0.4, 0.6],
        "velocity_distribution": ["normal", desired_speed, 0.1],  # Use specified desired speed
        "box": [3.6, 36.5, 3.6, 26.5],  # Initial position box
        "destination": "door"
    }]

    people = people_initialization(
        dom, groups, dt,
        dmin_people=dmin_people, dmin_walls=dmin_walls, seed=seed,
        itermax=10, projection_method=projection_method, verbose=verbose
    )

    I, J, Vd = dom.people_desired_velocity(
        people["xyrv"],
        people["destinations"]
    )
    people["Vd"] = Vd

    for ip, pid in enumerate(people["id"]):
        people["paths"][pid] = people["xyrv"][ip, :2]

    all_people = {domain_name: people}

    if verbose:
        print(f"Initial population: {people['xyrv'].shape[0]}")
        print(f"Parameters: speed={desired_speed}, F={repulsion_strength}, tau={relaxation_time}, door_width={door_width}")

    # Count people that have evacuated
    initial_count = people['xyrv'].shape[0]
    total_evacuated = 0
    last_evacuated_count = 0

    # For tracking when people leave
    exit_times = []
    people_count_over_time = []

    # Main simulation loop
    start_time = time.time()

    while t < Tf:
        people_count = all_people[domain_name]["xyrv"].shape[0]
        people_count_over_time.append((t, people_count))

        # Calculate the number of evacuated people in this timestep
        newly_evacuated = last_evacuated_count - people_count
        if newly_evacuated > 0:
            exit_times.extend([t] * newly_evacuated)

        last_evacuated_count = people_count

        # Check if all people have evacuated
        if people_count == 0:
            if verbose:
                print(f"All people evacuated at time {t}")
            metrics["evacuation_time"] = t
            break

        # Calculate metrics at regular intervals
        if t >= last_metric_time + metric_interval:
            # Count collisions
            if people_count > 0:
                contacts = compute_contacts(dom, all_people[domain_name]["xyrv"], dmax)
                metrics["collision_count"].append((t, len(contacts)))

                # Calculate density near exit
                people_at_exit = 0
                for person in range(all_people[domain_name]["xyrv"].shape[0]):
                    x, y = all_people[domain_name]["xyrv"][person, 0:2]
                    if (exit_area["x_min"] <= x <= exit_area["x_max"] and
                        exit_area["y_min"] <= y <= exit_area["y_max"]):
                        people_at_exit += 1

                density = people_at_exit / exit_area_size if exit_area_size > 0 else 0
                metrics["exit_density"].append((t, density))

                # Calculate flow rate (people per second) by counting how many people crossed
                # the sensor in the last interval
                evacuated_in_interval = len([et for et in exit_times if last_metric_time <= et < t])
                flow_rate = evacuated_in_interval / metric_interval
                metrics["flow_rate"].append((t, flow_rate))

            last_metric_time = t

        if verbose and (int(t) % 5 == 0):
            print(f"\n===> Time = {t:.2f}, People remaining: {people_count}")

        # Compute people desired velocity
        if people_count > 0:
            I, J, Vd = dom.people_desired_velocity(
                all_people[domain_name]["xyrv"],
                all_people[domain_name]["destinations"])
            all_people[domain_name]["Vd"] = Vd
            all_people[domain_name]["I"] = I
            all_people[domain_name]["J"] = J

            # Social forces calculation
            xyrv = all_people[domain_name]["xyrv"]
            Vd = all_people[domain_name]["Vd"]
            Uold = all_people[domain_name]["Uold"]

            contacts = compute_contacts(dom, xyrv, dmax)
            Forces = compute_forces(
                repulsion_strength,  # Use specified repulsion strength F
                repulsion_strength,  # Also use F for wall repulsion
                xyrv, contacts, Uold, Vd,
                lambda_, delta, kappa, eta
            )
            all_people[domain_name]["U"] = dt*(Vd-Uold)/relaxation_time + Uold + dt*Forces/mass  # Use specified relaxation time

            # Move people
            all_people[domain_name], all_sensors[domain_name] = move_people(
                t, dt, all_people[domain_name], all_sensors[domain_name])

            # Update people destinations
            all_people = people_update_destination(all_people, {domain_name: dom}, dom.pixel_size)

            # Update previous velocities
            all_people[domain_name]["Uold"] = all_people[domain_name]["U"]

        t += dt

        # Break if we reach time limit without evacuation
        if t >= Tf:
            if verbose:
                print(f"Simulation reached time limit {Tf} with {people_count} people remaining")
            metrics["evacuation_time"] = Tf  # Set to max time if not all evacuated

    # Calculate average metrics
    if metrics["flow_rate"]:
        metrics["avg_flow_rate"] = np.mean([fr[1] for fr in metrics["flow_rate"]])
    else:
        metrics["avg_flow_rate"] = 0

    if metrics["collision_count"]:
        metrics["avg_collision_rate"] = np.mean([cc[1] for cc in metrics["collision_count"]])
    else:
        metrics["avg_collision_rate"] = 0

    if metrics["exit_density"]:
        metrics["avg_exit_density"] = np.mean([ed[1] for ed in metrics["exit_density"]])
    else:
        metrics["avg_exit_density"] = 0

    sim_time = time.time() - start_time
    if verbose:
        print(f"Simulation completed in {sim_time:.2f} seconds")
        print(f"Evacuation time: {metrics['evacuation_time']:.2f} seconds")
        print(f"Average flow rate: {metrics['avg_flow_rate']:.2f} people/second")
        print(f"Average collision rate: {metrics['avg_collision_rate']:.2f} collisions")
        print(f"Average exit density: {metrics['avg_exit_density']:.2f} people/m²")

    return metrics


def run_parameter_sweep(parameter_ranges, repetitions=3):
    """
    Run simulations with different parameter combinations.

    Args:
        parameter_ranges: Dictionary with parameter ranges to test
        repetitions: Number of repetitions for each parameter combination

    Returns:
        Dictionary with results for each parameter combination
    """
    results = {}

    # Generate all parameter combinations
    param_names = list(parameter_ranges.keys())
    # param_values = list(parameter_ranges.values())

    # Simple parameter sweep (not full factorial)
    for param_name in param_names:
        param_results = {}
        base_params = {
            'num_people': 100,
            'desired_speed': 1.2,
            'repulsion_strength': 2000.0,
            'relaxation_time': 0.5,
            'door_width': 5
        }

        # For each value of the current parameter
        for value in parameter_ranges[param_name]:
            value_results = []
            print(f"\nTesting {param_name} = {value} ({repetitions} repetitions):")

            # Set the current parameter value while keeping others at default
            current_params = base_params.copy()
            current_params[param_name] = value

            # Run multiple repetitions
            for rep in range(repetitions):
                seed = 40 + rep  # Different seed for each repetition
                current_params['seed'] = seed

                print(f"  Rep {rep+1}: Running simulation... (seed:{seed})")
                metrics = run_simulation(**current_params)

                value_results.append(metrics)
                print(f"    Evacuation time: {metrics['evacuation_time']:.2f}s, "
                      f"Flow rate: {metrics['avg_flow_rate']:.2f} p/s, "
                      f"Collisions: {metrics['avg_collision_rate']:.2f}, "
                      f"Exit density: {metrics['avg_exit_density']:.2f} p/m²")

            # Calculate average metrics across repetitions
            avg_evac_time = np.mean([res['evacuation_time'] for res in value_results])
            std_evac_time = np.std([res['evacuation_time'] for res in value_results])

            avg_flow_rate = np.mean([res['avg_flow_rate'] for res in value_results])
            std_flow_rate = np.std([res['avg_flow_rate'] for res in value_results])

            avg_collision_rate = np.mean([res['avg_collision_rate'] for res in value_results])
            std_collision_rate = np.std([res['avg_collision_rate'] for res in value_results])

            avg_exit_density = np.mean([res['avg_exit_density'] for res in value_results])
            std_exit_density = np.std([res['avg_exit_density'] for res in value_results])

            param_results[value] = {
                'evacuation_time': {
                    'mean': avg_evac_time,
                    'std': std_evac_time
                },
                'flow_rate': {
                    'mean': avg_flow_rate,
                    'std': std_flow_rate
                },
                'collision_rate': {
                    'mean': avg_collision_rate,
                    'std': std_collision_rate
                },
                'exit_density': {
                    'mean': avg_exit_density,
                    'std': std_exit_density
                },
                'raw_results': value_results
            }

            print(f"  Average: Evacuation time = {avg_evac_time:.2f} ± {std_evac_time:.2f}s, "
                  f"Flow rate = {avg_flow_rate:.2f} ± {std_flow_rate:.2f} p/s")

        results[param_name] = param_results

    return results


def plot_parameter_results(results):
    """
    Plot results for each parameter variation
    """
    metrics = ['evacuation_time', 'flow_rate', 'collision_rate', 'exit_density']
    metric_labels = {
        'evacuation_time': 'Evacuation Time (s)',
        'flow_rate': 'Flow Rate (people/s)',
        'collision_rate': 'Collision Rate (colls./s)',
        'exit_density': 'Exit Density (people/m²)'
    }

    # Create a figure for each parameter
    for param_name, param_results in results.items():
        # Pretty parameter names
        param_labels = {
            'num_people': 'Number of People',
            'desired_speed': 'Desired Speed (m/s)',
            'repulsion_strength': 'Repulsion Strength (N)',
            'relaxation_time': 'Relaxation Time (s)',
            'door_width': 'Door Width (m)'
        }

        # Sort parameter values
        values = sorted(param_results.keys())

        fig, axs = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle(f'Effect of {param_labels[param_name]} on Evacuation Metrics', fontsize=16)

        for i, metric in enumerate(metrics):
            row, col = i // 2, i % 2
            ax = axs[row, col]

            means = [param_results[v][metric]['mean'] for v in values]
            stds = [param_results[v][metric]['std'] for v in values]

            ax.errorbar(values, means, yerr=stds, fmt='o-', capsize=5, elinewidth=1, markersize=8)
            ax.set_xlabel(param_labels[param_name], fontsize=12)
            ax.set_ylabel(metric_labels[metric], fontsize=12)
            ax.grid(True, alpha=0.3)

            # Add trend line
            coeffs = np.polyfit(values, means, 2)
            poly = np.poly1d(coeffs)
            x_smooth = np.linspace(min(values), max(values), 100)
            ax.plot(x_smooth, poly(x_smooth), 'r--', alpha=0.7)

        plt.tight_layout(rect=[0, 0, 1, 0.95])  # Make room for the title
        plt.savefig(f'parameter_sweep_{param_name}.png', dpi=300)

    plt.show()


if __name__ == "__main__":
    # Define parameter ranges to test
    parameter_ranges = {
        'num_people': range(5,200,2),
        # 'desired_speed': range(1,6),
        # 'repulsion_strength': [100, 500, 1000, 2000, 3000, 4000, 5000],
        # 'relaxation_time': [0.1, 0.5, 1.0, 1.5, 2.0, 3, 4, 5],
        # 'door_width': [1.0, 1.5, 2.0, 2.5, 3.0, 4, 5, 6, 10, 12]
    }
    # parameter_ranges = {
    #     'num_people': range(20,160,20),
    #     'desired_speed': range(1,6),
    #     'repulsion_strength': [100, 500, 1000, 2000, 3000, 4000, 5000],
    #     'relaxation_time': [0.1, 0.5, 1.0, 1.5, 2.0, 3, 4, 5],
    #     'door_width': [1.0, 1.5, 2.0, 2.5, 3.0, 4, 5, 6, 10, 12]
    # }
    # Start timing the entire operation
    overall_start_time = time.time()
    # Run parameter sweeps
    results = run_parameter_sweep(parameter_ranges, repetitions=5)
    # Print the end time
    overall_end_time = time.time()
    print(f"Total execution time: {overall_end_time - overall_start_time:.2f} seconds")
    # Save results to file
    with open('evacuation_parameter_sweep.json', 'w') as f:
        # Convert keys to strings for JSON serialization (numeric values as keys aren't supported)
        json_results = {}
        for param_name, param_results in results.items():
            json_results[param_name] = {str(k): v for k, v in param_results.items()}

        json.dump(json_results, f, indent=2)

    # Plot results
    plot_parameter_results(results)

    print("\nSimulation complete! Results saved to evacuation_parameter_sweep.json")
    print("Plots saved as parameter_sweep_*.png")
