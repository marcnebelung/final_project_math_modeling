import os
import json
import time
import numpy as np
import matplotlib.pyplot as plt
from cromosim.domain import Domain
from cromosim.domain import Destination
from cromosim.micro import people_initialization, compute_contacts
from cromosim.micro import compute_forces, move_people, people_update_destination


class SimulationMetrics:
    """
    Class to track and compute various metrics during simulation
    """
    def __init__(self):
        self.evacuation_time = 0.0
        self.exit_times = []  # List of times when agents exit
        self.flow_rates = []  # Flow rate over time (people/second)
        self.flow_rate_times = []  # Corresponding times for flow rates
        self.collision_counts = []  # Number of collisions per time step
        self.collision_times = []  # Corresponding times for collisions
        self.exit_densities = []  # Density near exit over time
        self.exit_density_times = []  # Corresponding times for exit densities
        self.velocity_variances = []  # Variance in velocity over time
        self.velocity_variance_times = []  # Corresponding times for velocity variances
        self.total_collisions = 0  # Total number of collisions
        self.initial_people_count = 0  # Number of people at start
        self.remaining_people = []  # People remaining over time
        self.remaining_people_times = []  # Corresponding times

        # Track agent positions and velocities for analyzing patterns
        self.agent_positions = {}  # Positions over time
        self.agent_velocities = {}  # Velocities over time

        # Parameters used in the simulation
        self.parameters = {}

    def add_exit_time(self, t):
        """Record time when an agent exits"""
        self.exit_times.append(t)

    def add_collision(self, t, count):
        """Record collision count at time t"""
        self.collision_counts.append(count)
        self.collision_times.append(t)
        self.total_collisions += count

    def add_exit_density(self, t, density):
        """Record density near exit at time t"""
        self.exit_densities.append(density)
        self.exit_density_times.append(t)

    def add_velocity_variance(self, t, variance):
        """Record velocity variance at time t"""
        self.velocity_variances.append(variance)
        self.velocity_variance_times.append(t)

    def update_flow_rate(self, t, interval=5.0):
        """Calculate flow rate at time t over the specified interval"""
        if not self.exit_times:
            self.flow_rates.append(0.0)
            self.flow_rate_times.append(t)
            return 0.0

        # Count exits in the last interval seconds
        recent_exits = sum(1 for exit_t in self.exit_times if t - interval < exit_t <= t)
        flow_rate = recent_exits / interval if interval > 0 else 0

        self.flow_rates.append(flow_rate)
        self.flow_rate_times.append(t)
        return flow_rate

    def update_remaining_people(self, t, count):
        """Update the count of remaining people at time t"""
        self.remaining_people.append(count)
        self.remaining_people_times.append(t)

    def calculate_metrics(self):
        """Calculate final metrics from collected data"""
        if not self.exit_times:
            return {
                "evacuation_time": self.evacuation_time,
                "average_flow_rate": 0.0,
                "peak_flow_rate": 0.0,
                "total_collisions": self.total_collisions,
                "average_collision_rate": 0.0,
                "average_exit_density": 0.0,
                "peak_exit_density": 0.0,
                "average_velocity_variance": 0.0
            }

        # Evacuation time (max exit time)
        self.evacuation_time = max(self.exit_times) if self.exit_times else 0.0

        # Average and peak flow rates
        avg_flow_rate = np.mean(self.flow_rates) if self.flow_rates else 0.0
        peak_flow_rate = np.max(self.flow_rates) if self.flow_rates else 0.0

        # Average collision rate (collisions per second)
        avg_collision_rate = 0.0
        if self.collision_counts and self.evacuation_time > 0:
            avg_collision_rate = sum(self.collision_counts) / self.evacuation_time

        # Average and peak exit densities
        avg_exit_density = np.mean(self.exit_densities) if self.exit_densities else 0.0
        peak_exit_density = np.max(self.exit_densities) if self.exit_densities else 0.0

        # Average velocity variance
        avg_velocity_variance = np.mean(self.velocity_variances) if self.velocity_variances else 0.0

        return {
            "evacuation_time": self.evacuation_time,
            "average_flow_rate": avg_flow_rate,
            "peak_flow_rate": peak_flow_rate,
            "total_collisions": self.total_collisions,
            "average_collision_rate": avg_collision_rate,
            "average_exit_density": avg_exit_density,
            "peak_exit_density": peak_exit_density,
            "average_velocity_variance": avg_velocity_variance
        }

    def plot_metrics(self, output_dir='plots'):
        """Generate plots for all metrics"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Plot remaining people over time
        plt.grid(True, alpha=0.3)

    # Add polynomial fit to show trend
    if len(values) > 2:
        coeffs = np.polyfit(values, evac_times, 2)
        poly = np.poly1d(coeffs)
        x_smooth = np.linspace(min(values), max(values), 100)
        plt.plot(x_smooth, poly(x_smooth), 'r--', alpha=0.7,
                label=f'Trend: {coeffs[0]:.4f}x² + {coeffs[1]:.2f}x + {coeffs[2]:.2f}')
        plt.legend()

    plt.tight_layout()
    plt.savefig(f'{output_dir}/evacuation_time_vs_{param_name}.png', dpi=300)
    plt.close()

    # Plot flow rate vs parameter
    plt.figure(figsize=(10, 6))
    plt.errorbar(values, flow_rates, yerr=flow_std, fmt='o-', capsize=5,
                 elinewidth=1, markersize=8)
    plt.xlabel(param_name, fontsize=14)
    plt.ylabel('Flow Rate (people/s)', fontsize=14)
    plt.title(f'Flow Rate vs {param_name}', fontsize=16)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/flow_rate_vs_{param_name}.png', dpi=300)
    plt.close()

    # Plot collisions vs parameter
    plt.figure(figsize=(10, 6))
    plt.errorbar(values, collisions, yerr=coll_std, fmt='o-', capsize=5,
                 elinewidth=1, markersize=8)
    plt.xlabel(param_name, fontsize=14)
    plt.ylabel('Collision Count', fontsize=14)
    plt.title(f'Collisions vs {param_name}', fontsize=16)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/collisions_vs_{param_name}.png', dpi=300)
    plt.close()

    # Plot exit density vs parameter
    plt.figure(figsize=(10, 6))
    plt.errorbar(values, exit_densities, yerr=density_std, fmt='o-', capsize=5,
                 elinewidth=1, markersize=8)
    plt.xlabel(param_name, fontsize=14)
    plt.ylabel('Exit Density (people/m²)', fontsize=14)
    plt.title(f'Exit Density vs {param_name}', fontsize=16)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/exit_density_vs_{param_name}.png', dpi=300)
    plt.close()

    # Plot velocity variance vs parameter
    plt.figure(figsize=(10, 6))
    plt.errorbar(values, vel_variances, yerr=var_std, fmt='o-', capsize=5,
                 elinewidth=1, markersize=8)
    plt.xlabel(param_name, fontsize=14)
    plt.ylabel('Velocity Variance', fontsize=14)
    plt.title(f'Velocity Variance vs {param_name}', fontsize=16)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/velocity_variance_vs_{param_name}.png', dpi=300)
    plt.close()


def compare_scenarios(scenarios, metrics=None, output_dir='comparisons'):
    """
    Compare multiple scenarios across different metrics.

    Parameters:
    -----------
    scenarios : dict
        Dictionary of scenario names and their results
    metrics : list, optional
        List of metrics to compare (default: all)
    output_dir : str, optional
        Directory to save output files

    Returns:
    --------
    None
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if not metrics:
        metrics = ['evacuation_time', 'flow_rate', 'collisions', 'exit_density', 'velocity_variance']

    # Labels for metrics
    metric_labels = {
        'evacuation_time': 'Evacuation Time (s)',
        'flow_rate': 'Flow Rate (people/s)',
        'collisions': 'Collision Count',
        'exit_density': 'Exit Density (people/m²)',
        'velocity_variance': 'Velocity Variance'
    }

    # Plot bar charts for each metric
    for metric in metrics:
        plt.figure(figsize=(12, 7))

        scenario_names = list(scenarios.keys())
        means = [scenarios[s][metric]['mean'] for s in scenario_names]
        stds = [scenarios[s][metric]['std'] for s in scenario_names]

        x = np.arange(len(scenario_names))
        width = 0.6

        bars = plt.bar(x, means, width, yerr=stds, capsize=10,
                     alpha=0.7, ecolor='black')

        plt.xlabel('Scenario', fontsize=14)
        plt.ylabel(metric_labels[metric], fontsize=14)
        plt.title(f'Comparison of {metric_labels[metric]} Across Scenarios', fontsize=16)
        plt.xticks(x, scenario_names, rotation=45, ha='right')
        plt.grid(True, alpha=0.3, axis='y')

        # Add values on top of bars
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.01*max(means),
                    f'{height:.2f}', ha='center', va='bottom', fontsize=10)

        plt.tight_layout()
        plt.savefig(f'{output_dir}/{metric}_comparison.png', dpi=300)
        plt.close()


def setup_baseline_scenario(num_people=50):
    """
    Set up the baseline evacuation scenario.

    Parameters:
    -----------
    num_people : int, optional
        Number of people to simulate

    Returns:
    --------
    params : dict
        Dictionary of parameters for the baseline scenario
    """
    return {
        "desired_speed": 1.34,  # m/s
        "F": 2.1,              # Repulsion strength (m²/s²)
        "tau": 0.5,            # Relaxation time (s)
        "exit_width": 1.5,     # m
        "Tf": 120.0,           # Simulation time limit
        "lambda": 0.5,         # Social force parameter
        "delta": 0.1,          # Social force parameter
    }


def setup_panic_scenario(num_people=50):
    """
    Set up the panic-induced congestion scenario.

    Parameters:
    -----------
    num_people : int, optional
        Number of people to simulate

    Returns:
    --------
    params : dict
        Dictionary of parameters for the panic scenario
    """
    return {
        "desired_speed": 2.5,  # m/s - high desired speed (panic)
        "F": 1.0,              # Reduced repulsion strength (m²/s²)
        "tau": 0.3,            # Short relaxation time (s)
        "exit_width": 1.5,     # m
        "Tf": 120.0,           # Simulation time limit
        "lambda": 0.3,         # Modified social force parameter
        "delta": 0.05,         # Modified social force parameter
    }


def setup_variable_exit_width_scenario(width, num_people=50):
    """
    Set up scenario with a specific exit width.

    Parameters:
    -----------
    width : float
        Exit width in meters
    num_people : int, optional
        Number of people to simulate

    Returns:
    --------
    params : dict
        Dictionary of parameters for the scenario
    """
    return {
        "desired_speed": 1.34,  # m/s
        "F": 2.1,              # Repulsion strength (m²/s²)
        "tau": 0.5,            # Relaxation time (s)
        "exit_width": width,   # Variable exit width (m)
        "Tf": 120.0,           # Simulation time limit
        "lambda": 0.5,         # Social force parameter
        "delta": 0.1,          # Social force parameter
    }


def setup_heterogeneous_crowd(num_people=50, fraction_slow=0.2):
    """
    Set up scenario with heterogeneous crowd (mix of slow and fast agents).
    This requires adapting the simulation code to handle multiple groups
    with different parameters.

    Parameters:
    -----------
    num_people : int, optional
        Total number of people to simulate
    fraction_slow : float
        Fraction of slow-moving agents (e.g., disabled, elderly)

    Returns:
    --------
    params : dict
        Dictionary of parameters for the scenario with multiple agent groups
    """
    num_slow = int(num_people * fraction_slow)
    num_fast = num_people - num_slow

    return {
        "multi_group": True,   # Flag for multiple groups
        "groups": [
            {
                "name": "slow",
                "count": num_slow,
                "desired_speed": 1.0,  # Slow agents (m/s)
                "tau": 0.8,            # Longer relaxation time
            },
            {
                "name": "fast",
                "count": num_fast,
                "desired_speed": 2.0,  # Fast agents (m/s)
                "tau": 0.4,            # Shorter relaxation time
            }
        ],
        "F": 2.1,              # Repulsion strength (m²/s²)
        "exit_width": 1.5,     # m
        "Tf": 120.0,           # Simulation time limit
        "lambda": 0.5,         # Social force parameter
        "delta": 0.1,          # Social force parameter
    }figure(figsize=(10, 6))
        plt.plot(self.remaining_people_times, self.remaining_people, 'b-', linewidth=2)
        plt.xlabel('Time (s)', fontsize=12)
        plt.ylabel('People Remaining', fontsize=12)
        plt.title('Evacuation Progress', fontsize=14)
        plt.grid(True, alpha=0.3)
        plt.savefig(f'{output_dir}/remaining_people.png', dpi=300)
        plt.close()

        # Plot flow rate over time
        if self.flow_rates:
            plt.figure(figsize=(10, 6))
            plt.plot(self.flow_rate_times, self.flow_rates, 'g-', linewidth=2)
            plt.xlabel('Time (s)', fontsize=12)
            plt.ylabel('Flow Rate (people/s)', fontsize=12)
            plt.title('Exit Flow Rate Over Time', fontsize=14)
            plt.grid(True, alpha=0.3)
            plt.savefig(f'{output_dir}/flow_rate.png', dpi=300)
            plt.close()

        # Plot collision rate over time
        if self.collision_counts:
            plt.figure(figsize=(10, 6))
            plt.plot(self.collision_times, self.collision_counts, 'r-', linewidth=2)
            plt.xlabel('Time (s)', fontsize=12)
            plt.ylabel('Collisions Count', fontsize=12)
            plt.title('Collisions Over Time', fontsize=14)
            plt.grid(True, alpha=0.3)
            plt.savefig(f'{output_dir}/collisions.png', dpi=300)
            plt.close()

        # Plot exit density over time
        if self.exit_densities:
            plt.figure(figsize=(10, 6))
            plt.plot(self.exit_density_times, self.exit_densities, 'm-', linewidth=2)
            plt.xlabel('Time (s)', fontsize=12)
            plt.ylabel('Density (people/m²)', fontsize=12)
            plt.title('Exit Density Over Time', fontsize=14)
            plt.grid(True, alpha=0.3)
            plt.savefig(f'{output_dir}/exit_density.png', dpi=300)
            plt.close()

        # Plot velocity variance over time
        if self.velocity_variances:
            plt.figure(figsize=(10, 6))
            plt.plot(self.velocity_variance_times, self.velocity_variances, 'c-', linewidth=2)
            plt.xlabel('Time (s)', fontsize=12)
            plt.ylabel('Velocity Variance', fontsize=12)
            plt.title('Velocity Variance Over Time', fontsize=14)
            plt.grid(True, alpha=0.3)
            plt.savefig(f'{output_dir}/velocity_variance.png', dpi=300)
            plt.close()


def run_simulation(num_people, param_dict=None, base_json_file='input_room.json', seed=None, verbose=False):
    """
    Run a single simulation with num_people individuals.

    Parameters:
    -----------
    num_people : int
        Number of people to simulate
    param_dict : dict, optional
        Dictionary of parameters to override in the JSON configuration
    base_json_file : str, optional
        Path to the base JSON configuration file
    seed : int, optional
        Random seed for reproducibility
    verbose : bool, optional
        Whether to print verbose output

    Returns:
    --------
    metrics : SimulationMetrics
        Object containing simulation metrics
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

    # Apply parameter overrides if provided
    if param_dict:
        for key, value in param_dict.items():
            if key in input_config:
                input_config[key] = value
            elif key == "desired_speed":
                # Apply desired speed to all groups
                for people_init in input_config["people_init"]:
                    for group in people_init["groups"]:
                        group["v"] = value
            elif key == "exit_width":
                # Update exit width (requires specific handling based on your domain)
                # This is just a placeholder - you'll need to adapt to your domain structure
                pass

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

    # Initialize metrics tracker
    metrics = SimulationMetrics()
    metrics.initial_people_count = people["xyrv"].shape[0]
    metrics.parameters = {
        "num_people": num_people,
        "tau": tau,
        "F": F,
        "Fwall": Fwall,
        "desired_speed": input_config["people_init"][0]["groups"][0].get("v", "N/A"),
        "seed": seed,
        **({} if param_dict is None else param_dict)
    }

    metrics.update_remaining_people(t, people["xyrv"].shape[0])

    if verbose:
        print(f"Initial population: {people['xyrv'].shape[0]}")

    # Define the exit area for density calculations
    # Adjust these values based on your domain and exit location
    exit_area = {
        "x_min": 0,  # Replace with actual coordinates
        "x_max": 0,  # Replace with actual coordinates
        "y_min": 0,  # Replace with actual coordinates
        "y_max": 0,  # Replace with actual coordinates
        "area": 0    # m²
    }

    # Determine exit area based on domain characteristics
    # This is a placeholder - you'll need to implement based on your domain
    try:
        exit_rect = dom.get_exit_area()
        if exit_rect:
            exit_area = exit_rect
    except:
        # If no method exists, use a default or calculate based on domain knowledge
        pass

    # Main simulation loop
    start_time = time.time()
    last_count = people["xyrv"].shape[0]
    collision_count = 0
    flow_rate_interval = 2.0  # seconds

    while t < Tf:
        # Update metrics
        current_count = all_people[jname]["xyrv"].shape[0] if jname in all_people else 0
        metrics.update_remaining_people(t, current_count)

        # Check if people have exited since last time step
        if current_count < last_count:
            # Record exit times for each person who exited
            for _ in range(last_count - current_count):
                metrics.add_exit_time(t)

        last_count = current_count

        # Check if all people have evacuated
        if all_people[jname]["xyrv"].shape[0] == 0:
            if verbose:
                print(f"All people evacuated at time {t}")
            break

        # Update flow rate periodically
        if int(t / flow_rate_interval) > int((t - dt) / flow_rate_interval):
            metrics.update_flow_rate(t, flow_rate_interval)

        # Verbose output
        if verbose and (int(t) % 5 == 0 and int(t) != int(t - dt)):
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

            # Compute contacts and count collisions
            contacts = compute_contacts(dom, xyrv, dmax)
            collision_count = sum(1 for c in contacts if c[2] < 0)
            metrics.add_collision(t, collision_count)

            # Calculate velocity variance
            if "U" in all_people[jname]:
                velocities = all_people[jname]["U"]
                if len(velocities) > 0:
                    velocity_magnitude = np.linalg.norm(velocities, axis=1)
                    velocity_variance = np.var(velocity_magnitude)
                    metrics.add_velocity_variance(t, velocity_variance)

            # Calculate exit density
            people_at_exit = 0
            for person_pos in xyrv[:, :2]:
                x, y = person_pos
                if (exit_area["x_min"] <= x <= exit_area["x_max"] and
                    exit_area["y_min"] <= y <= exit_area["y_max"]):
                    people_at_exit += 1

            if exit_area["area"] > 0:
                exit_density = people_at_exit / exit_area["area"]
                metrics.add_exit_density(t, exit_density)

            # Compute forces and update velocities
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
            metrics.evacuation_time = t

    sim_time = time.time() - start_time
    if verbose:
        print(f"Simulation completed in {sim_time:.2f} seconds")

    # Final metrics calculation
    metrics.evacuation_time = t
    final_metrics = metrics.calculate_metrics()

    if verbose:
        print("\nFinal metrics:")
        for key, value in final_metrics.items():
            print(f"  {key}: {value}")

    return metrics


def run_parameter_study(base_params, param_to_vary, values, num_people, repetitions=5,
                      base_json_file='input_room.json', output_dir='parameter_study'):
    """
    Run a parameter study varying one parameter while keeping others constant.

    Parameters:
    -----------
    base_params : dict
        Base parameters to use for all simulations
    param_to_vary : str
        Name of parameter to vary
    values : list
        List of values to use for the parameter
    num_people : int
        Number of people to simulate
    repetitions : int, optional
        Number of repetitions for each parameter value
    base_json_file : str, optional
        Path to the base JSON configuration file
    output_dir : str, optional
        Directory to save output files

    Returns:
    --------
    results : dict
        Dictionary of results for each parameter value
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    results = {}

    for value in values:
        print(f"\nRunning simulations with {param_to_vary} = {value} ({repetitions} repetitions)...")
        value_results = []

        # Create parameter dict with this value
        params = base_params.copy()
        params[param_to_vary] = value

        for rep in range(repetitions):
            seed = 40 + rep  # Use different seed for each repetition
            print(f"  Rep {rep+1}: Running...")

            # Run simulation with these parameters
            metrics = run_simulation(num_people, params, base_json_file, seed)

            if metrics:
                value_results.append(metrics)
                final_metrics = metrics.calculate_metrics()
                print(f"  Rep {rep+1}: Evacuation time = {final_metrics['evacuation_time']:.2f}s, " +
                      f"Flow rate = {final_metrics['average_flow_rate']:.2f} p/s, " +
                      f"Collisions = {final_metrics['total_collisions']}")
            else:
                print(f"  Rep {rep+1}: Failed")

        # Process results from all repetitions
        if value_results:
            # Create directory for this parameter value
            param_dir = f"{output_dir}/{param_to_vary}_{value}"
            if not os.path.exists(param_dir):
                os.makedirs(param_dir)

            # Calculate aggregate metrics
            evac_times = [m.calculate_metrics()["evacuation_time"] for m in value_results]
            flow_rates = [m.calculate_metrics()["average_flow_rate"] for m in value_results]
            collisions = [m.calculate_metrics()["total_collisions"] for m in value_results]
            exit_densities = [m.calculate_metrics()["average_exit_density"] for m in value_results]
            vel_variances = [m.calculate_metrics()["average_velocity_variance"] for m in value_results]

            # Calculate statistics
            result_summary = {
                "evacuation_time": {
                    "mean": np.mean(evac_times),
                    "std": np.std(evac_times),
                    "values": evac_times
                },
                "flow_rate": {
                    "mean": np.mean(flow_rates),
                    "std": np.std(flow_rates),
                    "values": flow_rates
                },
                "collisions": {
                    "mean": np.mean(collisions),
                    "std": np.std(collisions),
                    "values": collisions
                },
                "exit_density": {
                    "mean": np.mean(exit_densities),
                    "std": np.std(exit_densities),
                    "values": exit_densities
                },
                "velocity_variance": {
                    "mean": np.mean(vel_variances),
                    "std": np.std(vel_variances),
                    "values": vel_variances
                }
            }

            # Save result summary
            with open(f"{param_dir}/summary.json", "w") as f:
                json.dump(result_summary, f, indent=2)

            # Save plot of one representative run
            value_results[0].plot_metrics(output_dir=param_dir)

            # Store results
            results[value] = result_summary

            print(f"  Average: Evacuation time = {result_summary['evacuation_time']['mean']:.2f} ± " +
                  f"{result_summary['evacuation_time']['std']:.2f}s, " +
                  f"Flow rate = {result_summary['flow_rate']['mean']:.2f} ± " +
                  f"{result_summary['flow_rate']['std']:.2f} p/s")
        else:
            print("  All simulations failed for this parameter value")

    # Create summary plots across all parameter values
    plot_parameter_study_results(results, param_to_vary, output_dir)

    return results


def run_scenario(scenario_name, num_people, params, repetitions=5, base_json_file='input_room.json',
                output_dir='scenarios'):
    """
    Run a specific scenario with a set of parameters.

    Parameters:
    -----------
    scenario_name : str
        Name of the scenario
    num_people : int
        Number of people to simulate
    params : dict
        Parameters to use for the simulation
    repetitions : int, optional
        Number of repetitions
    base_json_file : str, optional
        Path to the base JSON configuration file
    output_dir : str, optional
        Directory to save output files

    Returns:
    --------
    results : dict
        Dictionary of results
    """
    scenario_dir = f"{output_dir}/{scenario_name}"
    if not os.path.exists(scenario_dir):
        os.makedirs(scenario_dir)

    print(f"\nRunning scenario '{scenario_name}' ({repetitions} repetitions)...")

    # Save scenario parameters
    with open(f"{scenario_dir}/params.json", "w") as f:
        json.dump(params, f, indent=2)

    # Run multiple repetitions
    all_metrics = []

    for rep in range(repetitions):
        seed = 40 + rep  # Use different seed for each repetition
        print(f"  Rep {rep+1}: Running...")

        # Run simulation with these parameters
        metrics = run_simulation(num_people, params, base_json_file, seed)

        if metrics:
            all_metrics.append(metrics)
            final_metrics = metrics.calculate_metrics()
            print(f"  Rep {rep+1}: Evacuation time = {final_metrics['evacuation_time']:.2f}s, " +
                  f"Flow rate = {final_metrics['average_flow_rate']:.2f} p/s, " +
                  f"Collisions = {final_metrics['total_collisions']}")

            # Save plots for this repetition
            rep_dir = f"{scenario_dir}/rep_{rep+1}"
            if not os.path.exists(rep_dir):
                os.makedirs(rep_dir)
            metrics.plot_metrics(output_dir=rep_dir)
        else:
            print(f"  Rep {rep+1}: Failed")

    # Process results from all repetitions
    if all_metrics:
        # Calculate aggregate metrics
        evac_times = [m.calculate_metrics()["evacuation_time"] for m in all_metrics]
        flow_rates = [m.calculate_metrics()["average_flow_rate"] for m in all_metrics]
        collisions = [m.calculate_metrics()["total_collisions"] for m in all_metrics]
        exit_densities = [m.calculate_metrics()["average_exit_density"] for m in all_metrics]
        vel_variances = [m.calculate_metrics()["average_velocity_variance"] for m in all_metrics]

        # Calculate statistics
        result_summary = {
            "evacuation_time": {
                "mean": np.mean(evac_times),
                "std": np.std(evac_times),
                "values": evac_times
            },
            "flow_rate": {
                "mean": np.mean(flow_rates),
                "std": np.std(flow_rates),
                "values": flow_rates
            },
            "collisions": {
                "mean": np.mean(collisions),
                "std": np.std(collisions),
                "values": collisions
            },
            "exit_density": {
                "mean": np.mean(exit_densities),
                "std": np.std(exit_densities),
                "values": exit_densities
            },
            "velocity_variance": {
                "mean": np.mean(vel_variances),
                "std": np.std(vel_variances),
                "values": vel_variances
            }
        }

        # Save result summary
        with open(f"{scenario_dir}/summary.json", "w") as f:
            json.dump(result_summary, f, indent=2)

        print(f"  Average: Evacuation time = {result_summary['evacuation_time']['mean']:.2f} ± " +
              f"{result_summary['evacuation_time']['std']:.2f}s, " +
              f"Flow rate = {result_summary['flow_rate']['mean']:.2f} ± " +
              f"{result_summary['flow_rate']['std']:.2f} p/s")

        return result_summary
    else:
        print("  All simulations failed for this scenario")
        return None


def plot_parameter_study_results(results, param_name, output_dir):
    """
    Plot results from a parameter study.

    Parameters:
    -----------
    results : dict
        Dictionary of results for each parameter value
    param_name : str
        Name of the parameter that was varied
    output_dir : str
        Directory to save output files
    """
    # Extract parameter values and corresponding metrics
    values = sorted(results.keys())
    evac_times = [results[v]["evacuation_time"]["mean"] for v in values]
    evac_std = [results[v]["evacuation_time"]["std"] for v in values]
    flow_rates = [results[v]["flow_rate"]["mean"] for v in values]
    flow_std = [results[v]["flow_rate"]["std"] for v in values]
    collisions = [results[v]["collisions"]["mean"] for v in values]
    coll_std = [results[v]["collisions"]["std"] for v in values]
    exit_densities = [results[v]["exit_density"]["mean"] for v in values]
    density_std = [results[v]["exit_density"]["std"] for v in values]
    vel_variances = [results[v]["velocity_variance"]["mean"] for v in values]
    var_std = [results[v]["velocity_variance"]["std"] for v in values]

    # Plot evacuation time vs parameter
    plt.figure(figsize=(10, 6))
    plt.errorbar(values, evac_times, yerr=evac_std, fmt='o-', capsize=5,
                 elinewidth=1, markersize=8)
    plt.xlabel(param_name, fontsize=14)
    plt.ylabel('Evacuation Time (s)', fontsize=14)
    plt.title(f'Evacuation Time vs {param_name}', fontsize=16)
    plt
