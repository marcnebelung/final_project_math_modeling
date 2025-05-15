import os
import sys
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Ellipse, Rectangle, Polygon
from matplotlib.lines import Line2D

# Add the parent directory to the system path to resolve the module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import functions from parameter_sweep_simulation
from enhanced_sim.parameter_sweep_simulation import (
    create_domain,
    create_sensor
)
from create_animation import create_animation_from_frames

# Import required functions from cromosim
from cromosim.domain import Destination
from cromosim.micro import (
    people_initialization,
    plot_people,
    plot_sensors,
    move_people,
    people_update_destination,
    compute_forces,
    compute_contacts
)

def run_single_simulation(
    # Simulation parameters
    prefix="results/",
    num_people=50,
    desired_speed=1.2,
    repulsion_strength=2000.0,
    relaxation_time=0.5,
    door_width=1.5,
    seed=43,
    Tf=60.0,
    dt=0.005,
    drawper=20,

    # Visualization parameters
    with_graphes=True,
    plot_p=True,      # Plot people
    plot_c=False,      # Plot contacts
    plot_v=False,      # Plot velocities
    plot_vd=False,     # Plot desired velocities
    plot_s=True,      # Plot sensors
    plot_pa=False,     # Plot paths

    # Other model parameters
    mass=80.0,
    kappa=120000.0,
    delta=0.08,
    lambda_=0.5,
    eta=240000.0,
    dmax=0.1,
    dmin_people=0.0,
    dmin_walls=0.0,
    projection_method="cvxopt"
):
    """
    Run a single simulation with visualizations.

    Args:
        prefix: Directory to save results
        num_people: Number of people in the simulation
        desired_speed: Desired walking speed (m/s)
        repulsion_strength: Strength of repulsion forces (N)
        relaxation_time: Relaxation time parameter (s)
        door_width: Width of the exit door (m)
        seed: Random seed
        Tf: Final simulation time (s)
        dt: Time step (s)
        drawper: Draw every 'drawper' iterations
        with_graphes: Enable visualization
        plot_p: Plot people
        plot_c: Plot contacts
        plot_v: Plot velocities
        plot_vd: Plot desired velocities
        plot_s: Plot sensor
        plot_pa: Plot paths
        mass: Mass of a person (kg)
        kappa: Stiffness constant for overlapping
        delta: Distance to maintain from neighbors (m)
        lambda_: Directional dependence parameter
        eta: Friction coefficient
        dmax: Maximum neighbor detection distance
        dmin_people: Minimum allowed distance between people
        dmin_walls: Minimum allowed distance to walls
        projection_method: Method for projection calculations

    Returns:
        Dictionary with simulation metrics
    """
    print(f"===> Running single simulation with parameters:")
    print(f"     - Number of people: {num_people}")
    print(f"     - Desired speed: {desired_speed} m/s")
    print(f"     - Repulsion strength: {repulsion_strength} N")
    print(f"     - Relaxation time: {relaxation_time} s")
    print(f"     - Door width: {door_width} m")

    # Create domain with specified door width
    dom = create_domain(door_width)
    domain_name = dom.name

    # Display domain information
    print(f"===> Domain: {dom}")
    if with_graphes:
        dom.plot(id=100)
        dom.plot_wall_dist(id=101, step=20)

    # Create sensors
    sensor = create_sensor(dom)
    all_sensors = {domain_name: [sensor]}

    # Initialize simulation time
    t = 0.0
    counter = 0

    # Initialize people
    groups = [{
        "nb": num_people,
        "radius_distribution": ["uniform", 0.4, 0.6],
        "velocity_distribution": ["normal", desired_speed, 0.1],
        "box": [3.6, 36.5, 3.6, 26.5],  # Initial position box
        "destination": "door"
    }]

    people = people_initialization(
        dom, groups, dt,
        dmin_people=dmin_people, dmin_walls=dmin_walls, seed=seed,
        itermax=10, projection_method=projection_method, verbose=True
    )

    I, J, Vd = dom.people_desired_velocity(
        people["xyrv"],
        people["destinations"]
    )
    people["Vd"] = Vd

    for ip, pid in enumerate(people["id"]):
        people["paths"][pid] = people["xyrv"][ip, :2]

    contacts = None
    if with_graphes:
        colors = people["xyrv"][:, 2]  # Color based on radius
        plot_people(120, dom, people, contacts, colors, time=t,
                    plot_people=plot_p, plot_contacts=plot_c,
                    plot_velocities=plot_v, plot_desired_velocities=plot_vd,
                    plot_sensors=plot_s, sensors=all_sensors[dom.name],
                    savefig=True, filename=f"{prefix}{dom.name}_fig_{str(counter).zfill(6)}.png")

    all_people = {domain_name: people}

    print(f"===> Initial population: {people['xyrv'].shape[0]}")

    # Main simulation loop
    cc = 0
    draw = True
    virtual_people = {domain_name: {"xyrv": np.empty((0, 4)), "Vd": np.empty((0, 2)), "Uold": np.empty((0, 2)), "U": np.empty((0, 2))}}

    sim_start_time = time.time()

    while t < Tf:
        print(f"\n===> Time = {t}")

        # Get current population count
        people_count = all_people[domain_name]["xyrv"].shape[0]
        if people_count == 0:
            print(f"All people evacuated at time {t}")
            break

        # Compute people desired velocity
        print(f"===> Compute desired velocity for domain {domain_name}")
        I, J, Vd = dom.people_desired_velocity(
            all_people[domain_name]["xyrv"],
            all_people[domain_name]["destinations"]
        )
        all_people[domain_name]["Vd"] = Vd
        all_people[domain_name]["I"] = I
        all_people[domain_name]["J"] = J

        # Social forces calculation
        print(f"===> Compute social forces for domain {domain_name}")
        xyrv = all_people[domain_name]["xyrv"]
        Vd = all_people[domain_name]["Vd"]
        Uold = all_people[domain_name]["Uold"]

        if xyrv.shape[0] > 0:
            if np.unique(xyrv, axis=0).shape[0] != xyrv.shape[0]:
                print("===> ERROR: There are two identical lines in the array xyrv")
                sys.exit()

            contacts = compute_contacts(dom, xyrv, dmax)
            print(f"     Number of contacts: {contacts.shape[0]}")

            Forces = compute_forces(
                repulsion_strength,  # Use specified repulsion strength F
                repulsion_strength,  # Also use F for wall repulsion
                xyrv, contacts, Uold, Vd,
                lambda_, delta, kappa, eta
            )

            all_people[domain_name]["U"] = dt*(Vd-Uold)/relaxation_time + Uold + dt*Forces/mass

            # Move people
            all_people[domain_name], all_sensors[domain_name] = move_people(
                t, dt, all_people[domain_name], all_sensors[domain_name]
            )

            # Draw visualization
            if draw and with_graphes:
                # Coloring people according to their radius
                colors = all_people[domain_name]["xyrv"][:, 2]

                plot_people(120, dom, all_people[domain_name], contacts,
                            colors, virtual_people=virtual_people[domain_name], time=t,
                            plot_people=plot_p, plot_contacts=plot_c,
                            plot_paths=plot_pa, plot_velocities=plot_v,
                            plot_desired_velocities=plot_vd, plot_sensors=plot_s,
                            sensors=all_sensors[domain_name], savefig=True,
                            filename=f"{prefix}{dom.name}_fig_{str(counter).zfill(6)}.png")

        # Update people destinations
        all_people = people_update_destination(all_people, {domain_name: dom}, dom.pixel_size)

        # Update previous velocities
        all_people[domain_name]["Uold"] = all_people[domain_name]["U"]

        # Print the number of persons for each domain
        print(f"===> Domain {domain_name}, people remaining = {all_people[domain_name]['xyrv'].shape[0]}")

        t += dt
        cc += 1
        counter += 1
        if cc >= drawper:
            draw = True
            cc = 0
        else:
            draw = False

    sim_time = time.time() - sim_start_time
    print(f"\n===> Simulation completed in {sim_time:.2f} seconds")
    print(f"===> Final time: {t:.2f} seconds")
    print(f"===> Remaining people: {all_people[domain_name]['xyrv'].shape[0]}")

    # Plot sensor data at the end
    if with_graphes:
        plot_sensors(140, all_sensors[domain_name], t, savefig=True,
                     filename=f"{prefix}sensor_{counter}.png")

    # Basic metrics
    metrics = {
        "final_time": t,
        "remaining_people": all_people[domain_name]["xyrv"].shape[0],
        "evacuation_time": t if all_people[domain_name]["xyrv"].shape[0] == 0 else None,
        "people_evacuated": num_people - all_people[domain_name]["xyrv"].shape[0],
        "simulation_time": sim_time
    }

    return metrics

if __name__ == "__main__":
    # You can modify these parameters to test different scenarios

    params = {
        "prefix": "results/",
        "num_people": 100,
        "desired_speed": 5,
        "repulsion_strength": 1000.0,
        "relaxation_time": 0.5,
        "door_width": 5,
        "seed": 44,
        "Tf": 60.0,
        "dt": 0.005,
        "drawper": 10,  # Draw every 20 iterations
        "with_graphes": True
    }

    # Create output directory if it doesn't exist
    prefix = params['prefix']
    i = 0
    original_prefix = prefix
    while os.path.exists(prefix):
        prefix = f"{original_prefix.rstrip('/')}_{i}/"
        i += 1
    os.makedirs(prefix)
    params["prefix"] = prefix


    # Run the simulation
    metrics = run_single_simulation(**params)

    # Print final metrics
    print("\n===> Final Metrics:")
    for key, value in metrics.items():
        print(f"     - {key}: {value}")

    # Create animation from frames
    if params["with_graphes"]:

        real_time_fps = 1/params["dt"]/params["drawper"]
        desired_vid_length = 10
        fps_scaling = metrics["final_time"] / desired_vid_length
        fps = real_time_fps * fps_scaling

        create_animation_from_frames(params["prefix"], "room", fps=fps)

    plt.ioff()
    plt.show()
