import os
import json
import time
import numpy as np
import matplotlib.pyplot as plt
from cromosim.domain import Domain
from cromosim.domain import Destination
from cromosim.micro import people_initialization, compute_contacts
from cromosim.micro import compute_forces, move_people, people_update_destination


def run_simulation(num_people, base_json_file='input_room.json', seed=None, verbose=False):
    """
    Run a single simulation with num_people individuals.
    Returns the evacuation time.
    """
    # Load the base JSON configuration
    with open(base_json_file) as json_file:
        try:
            input_config = json.load(json_file)
        except json.JSONDecodeError as msg:
            print(f"Failed to load json file {base_json_file}: {msg}")
            return None

    # Update the number of people in the configuration
    input_config["people_init"][0]["groups"][0]["nb"] = num_people

    # If seed is provided, use it
    if seed is not None:
        input_config["seed"] = seed

    # Create output directory if it doesn't exist
    prefix = input_config["prefix"]
    if not os.path.exists(prefix):
        os.makedirs(prefix)

    # Set key simulation parameters
    seed = input_config["seed"]
    Tf = input_config["Tf"]
    dt = input_config["dt"]
    mass = input_config["mass"]
    tau = input_config["tau"]
    F = input_config["F"]
    kappa = input_config["kappa"]
    delta = input_config["delta"]
    Fwall = input_config["Fwall"]
    lambda_ = input_config["lambda"]
    eta = input_config["eta"]
    projection_method = input_config["projection_method"]
    dmax = input_config["dmax"]
    dmin_people = input_config["dmin_people"]
    dmin_walls = input_config["dmin_walls"]

    # Create the domain (we know there's only one)
    jdom = input_config["domains"][0]
    jname = jdom["name"]
    jpx = jdom["px"]
    jwall_colors = jdom["wall_colors"]

    dom = Domain(name=jname, background=jdom["background"], pixel_size=jpx, wall_colors=jwall_colors)
    dom.build_domain()

    # Add the destination (we know there's only one)
    dest_data = jdom["destinations"][0]
    dest = Destination(
        name=dest_data["name"],
        colors=dest_data["colors"],
        excluded_colors=dest_data["excluded_colors"],
        desired_velocity_from_color=[],
        velocity_scale=dest_data["velocity_scale"],
        next_destination=None,
        next_domain=None,
        next_transit_box=None
    )
    dom.add_destination(dest)

    # Create sensor (we know there's only one)
    sensor = input_config["sensors"][0]
    sensor["id"] = []
    sensor["times"] = []
    sensor["xy"] = []
    sensor["dir"] = []
    all_sensors = {jname: [sensor]}

    # Initialize simulation
    t = 0.0

    # Initialize people
    peopledom = input_config["people_init"][0]
    groups = peopledom["groups"]

    people = people_initialization(
        dom, groups, dt,
        dmin_people=dmin_people, dmin_walls=dmin_walls, seed=seed,
        itermax=10, projection_method=projection_method, verbose=verbose)

    I, J, Vd = dom.people_desired_velocity(
        people["xyrv"],
        people["destinations"])
    people["Vd"] = Vd

    for ip, pid in enumerate(people["id"]):
        people["paths"][pid] = people["xyrv"][ip, :2]

    all_people = {jname: people}

    if verbose:
        print(f"Initial population: {people['xyrv'].shape[0]}")

    # Main simulation loop
    start_time = time.time()

    while t < Tf:
        # Check if all people have evacuated
        if all_people[jname]["xyrv"].shape[0] == 0:
            if verbose:
                print(f"All people evacuated at time {t}")
            break

        if verbose and (int(t) % 5 == 0):
            print(f"\n===> Time = {t:.2f}, People remaining: {all_people[jname]['xyrv'].shape[0]}")

        # Compute people desired velocity
        if all_people[jname]["xyrv"].shape[0] > 0:
            I, J, Vd = dom.people_desired_velocity(
                all_people[jname]["xyrv"],
                all_people[jname]["destinations"])
            all_people[jname]["Vd"] = Vd
            all_people[jname]["I"] = I
            all_people[jname]["J"] = J

            # Social forces calculation
            xyrv = all_people[jname]["xyrv"]
            Vd = all_people[jname]["Vd"]
            Uold = all_people[jname]["Uold"]

            contacts = compute_contacts(dom, xyrv, dmax)
            Forces = compute_forces(F, Fwall, xyrv, contacts, Uold, Vd,
                                    lambda_, delta, kappa, eta)
            all_people[jname]["U"] = dt*(Vd-Uold)/tau + Uold + dt*Forces/mass

            # Move people
            all_people[jname], all_sensors[jname] = move_people(
                t, dt, all_people[jname], all_sensors[jname])

            # Update people destinations
            all_people = people_update_destination(all_people, {jname: dom}, dom.pixel_size)

            # Update previous velocities
            all_people[jname]["Uold"] = all_people[jname]["U"]

        t += dt

        # Break if we reach time limit without evacuation
        if t >= Tf:
            if verbose:
                print(f"Simulation reached time limit {Tf} with {all_people[jname]['xyrv'].shape[0]} people remaining")
            return t  # Return Tf if evacuation is incomplete

    sim_time = time.time() - start_time
    if verbose:
        print(f"Simulation completed in {sim_time:.2f} seconds")

    return t  # Return actual evacuation time


def run_multiple_simulations(people_counts, repetitions=5, base_json_file='input_room.json'):
    """
    Run multiple simulations for each population size and return results.
    """
    results = {}

    for n in people_counts:
        print(f"Running simulations for {n} people ({repetitions} repetitions)...")
        times = []

        for rep in range(repetitions):
            seed = 40 + rep  # Use different seed for each repetition
            evacuation_time = run_simulation(n, base_json_file, seed)
            if evacuation_time is not None:
                times.append(evacuation_time)
                print(f"  Rep {rep+1}: {evacuation_time:.2f} seconds")
            else:
                print(f"  Rep {rep+1}: Failed")

        # Calculate statistics
        if times:
            mean_time = np.mean(times)
            std_time = np.std(times)
            results[n] = {
                'times': times,
                'mean': mean_time,
                'std': std_time
            }
            print(f"  Average: {mean_time:.2f} ± {std_time:.2f} seconds")
        else:
            print("  All simulations failed for this population size")

    return results


def plot_evacuation_results(results):
    """
    Plot evacuation time vs. population size with error bars.
    """
    people_counts = sorted(results.keys())
    mean_times = [results[n]['mean'] for n in people_counts]
    std_times = [results[n]['std'] for n in people_counts]

    plt.figure(figsize=(10, 6))
    plt.errorbar(people_counts, mean_times, yerr=std_times, fmt='o-',
                 capsize=5, elinewidth=1, markersize=8)

    plt.xlabel('Number of People', fontsize=14)
    plt.ylabel('Evacuation Time (s)', fontsize=14)
    plt.title('Evacuation Time vs. Population Size', fontsize=16)
    plt.grid(True, alpha=0.3)

    # Add polynomial fit to show trend
    coeffs = np.polyfit(people_counts, mean_times, 2)
    poly = np.poly1d(coeffs)
    x_smooth = np.linspace(min(people_counts), max(people_counts), 100)
    plt.plot(x_smooth, poly(x_smooth), 'r--', alpha=0.7,
             label=f'Trend: {coeffs[0]:.4f}x² + {coeffs[1]:.2f}x + {coeffs[2]:.2f}')

    plt.legend()
    plt.tight_layout()
    plt.savefig('evacuation_results.png', dpi=300)
    plt.show()

    return coeffs


if __name__ == "__main__":
    # Define population sizes to test
    population_sizes = [10, 25, 50, 75, 100, 150]

    # Number of repetitions for each population size
    repetitions = 5

    # Run simulations
    results = run_multiple_simulations(population_sizes, repetitions)

    # Save results to file
    with open('evacuation_results.json', 'w') as f:
        json.dump({str(k): v for k, v in results.items()}, f, indent=2)

    # Plot results
    coeffs = plot_evacuation_results(results)

    print("\nResults summary:")
    print("---------------")
    for n in sorted(results.keys()):
        print(f"Population {n}: {results[n]['mean']:.2f} ± {results[n]['std']:.2f} seconds")

    print(f"\nTrend equation: {coeffs[0]:.4f}x² + {coeffs[1]:.2f}x + {coeffs[2]:.2f}")
