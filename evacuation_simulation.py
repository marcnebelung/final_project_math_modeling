import sys
import os
import json
import copy
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Ellipse, Rectangle, Polygon
from matplotlib.lines import Line2D
from cromosim.domain import Domain
from cromosim.domain import Destination
from cromosim.micro import people_initialization, plot_people, plot_sensors
from cromosim.micro import find_duplicate_people, compute_contacts
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
    for group in input_config["people_init"]:
        for g in group["groups"]:
            g["nb"] = num_people
    
    # If seed is provided, use it
    if seed is not None:
        input_config["seed"] = seed
    
    # Create output directory if it doesn't exist
    prefix = input_config["prefix"]
    if not os.path.exists(prefix):
        os.makedirs(prefix)
    
    # Set key simulation parameters
    seed = input_config["seed"]
    with_graphes = False  # Disable graphics for speed
    Tf = input_config["Tf"]
    dt = input_config["dt"]
    drawper = input_config["drawper"]
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
    
    # Create the domains
    domains = {}
    for i, jdom in enumerate(input_config["domains"]):
        jname = jdom["name"]
        if verbose:
            print(f"===> Build domain number {i}: {jname}")
        
        jbg = jdom["background"]
        jpx = jdom["px"]
        jwidth = jdom["width"]
        jheight = jdom["height"]
        jwall_colors = jdom["wall_colors"]
        
        if (jbg == ""):
            dom = Domain(name=jname, pixel_size=jpx, width=jwidth,
                         height=jheight, wall_colors=jwall_colors)
        else:
            dom = Domain(name=jname, background=jbg, pixel_size=jpx,
                         wall_colors=jwall_colors)
        
        # Add shapes to the domain
        for sl in jdom["shape_lines"]:
            line = Line2D(sl["xx"], sl["yy"], linewidth=sl["linewidth"])
            dom.add_shape(line, outline_color=sl["outline_color"],
                          fill_color=sl["fill_color"])
            
        for sc in jdom["shape_circles"]:
            circle = Circle((sc["center_x"], sc["center_y"]), sc["radius"])
            dom.add_shape(circle, outline_color=sc["outline_color"],
                          fill_color=sc["fill_color"])
            
        for se in jdom["shape_ellipses"]:
            ellipse = Ellipse((se["center_x"], se["center_y"]),
                              se["width"], se["height"],
                              se["angle_in_degrees_anti-clockwise"])
            dom.add_shape(ellipse, outline_color=se["outline_color"],
                          fill_color=se["fill_color"])
            
        for sr in jdom["shape_rectangles"]:
            rectangle = Rectangle((sr["bottom_left_x"], sr["bottom_left_y"]),
                                  sr["width"], sr["height"],
                                  sr["angle_in_degrees_anti-clockwise"])
            dom.add_shape(rectangle, outline_color=sr["outline_color"],
                          fill_color=sr["fill_color"])
            
        for spo in jdom["shape_polygons"]:
            polygon = Polygon(spo["xy"])
            dom.add_shape(polygon, outline_color=spo["outline_color"],
                          fill_color=spo["fill_color"])
        
        # Build the domain
        dom.build_domain()
        
        # Add destinations
        for j, dd in enumerate(jdom["destinations"]):
            desired_velocity_from_color = []
            for gg in dd["desired_velocity_from_color"]:
                desired_velocity_from_color.append(
                    np.concatenate((gg["color"], gg["desired_velocity"])))
            dest = Destination(
                name=dd["name"], colors=dd["colors"],
                excluded_colors=dd["excluded_colors"],
                desired_velocity_from_color=desired_velocity_from_color,
                velocity_scale=dd["velocity_scale"],
                next_destination=dd["next_destination"],
                next_domain=dd["next_domain"],
                next_transit_box=dd["next_transit_box"])
            dom.add_destination(dest)
        
        domains[dom.name] = dom
    
    # Create sensors
    all_sensors = {}
    for domain_name in domains:
        all_sensors[domain_name] = []
    for s in input_config["sensors"]:
        s["id"] = []
        s["times"] = []
        s["xy"] = []
        s["dir"] = []
        all_sensors[s["domain"]].append(s)
    
    # Initialize simulation
    t = 0.0
    counter = 0
    
    # Initialize people
    all_people = {}
    initial_count = 0
    for i, peopledom in enumerate(input_config["people_init"]):
        dom = domains[peopledom["domain"]]
        groups = peopledom["groups"]
        if verbose:
            print(f"===> Group number {i}, domain = {peopledom['domain']}")
        
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
        
        all_people[peopledom["domain"]] = people
        initial_count += people["xyrv"].shape[0]
    
    if verbose:
        print(f"Initial population: {initial_count}")
    
    # Main simulation loop
    cc = 0
    draw = False
    
    start_time = time.time()
    while t < Tf:
        # Stop if all people have evacuated
        total_people = sum(all_people[name]["xyrv"].shape[0] for name in domains)
        if total_people == 0:
            if verbose:
                print(f"All people evacuated at time {t}")
            break
            
        if verbose and (int(t) % 5 == 0):
            print(f"\n===> Time = {t:.2f}, People remaining: {total_people}")
        
        # Compute people desired velocity
        for idom, name in enumerate(domains):
            dom = domains[name]
            people = all_people[name]
            if people["xyrv"].shape[0] > 0:
                I, J, Vd = dom.people_desired_velocity(
                    people["xyrv"],
                    people["destinations"])
                people["Vd"] = Vd
                people["I"] = I
                people["J"] = J
        
        # Look for people in transit boxes
        virtual_people = find_duplicate_people(all_people, domains)
        
        # Social forces
        for idom, name in enumerate(domains):
            dom = domains[name]
            people = all_people[name]
            
            if people["xyrv"].shape[0] > 0:
                try:
                    xyrv = np.concatenate((people["xyrv"], virtual_people[name]["xyrv"]))
                    Vd = np.concatenate((people["Vd"], virtual_people[name]["Vd"]))
                    Uold = np.concatenate((people["Uold"], virtual_people[name]["Uold"]))
                except:
                    xyrv = people["xyrv"]
                    Vd = people["Vd"]
                    Uold = people["Uold"]
                
                if xyrv.shape[0] > 0:
                    if np.unique(xyrv, axis=0).shape[0] != xyrv.shape[0]:
                        print("===> ERROR: There are duplicate position entries in xyrv")
                        return None
                    
                    contacts = compute_contacts(dom, xyrv, dmax)
                    Forces = compute_forces(F, Fwall, xyrv, contacts, Uold, Vd,
                                            lambda_, delta, kappa, eta)
                    nn = people["xyrv"].shape[0]
                    all_people[name]["U"] = dt*(Vd[:nn, :]-Uold[:nn, :])/tau + \
                        Uold[:nn, :] + dt*Forces[:nn, :]/mass
                    
                    # Only for virtual people
                    if nn < Forces.shape[0]:
                        virtual_people[name]["U"] = dt*(Vd[nn:, :]-Uold[nn:, :])/tau + \
                            Uold[nn:, :] + dt*Forces[nn:, :]/mass
                    
                    all_people[name], all_sensors[name] = move_people(
                        t, dt, all_people[name], all_sensors[name])
        
        # Update people destinations
        all_people = people_update_destination(all_people, domains, dom.pixel_size)
        
        # Update previous velocities
        for name in domains:
            all_people[name]["Uold"] = all_people[name]["U"]
        
        t += dt
        cc += 1
        counter += 1
        if cc >= drawper:
            draw = True
            cc = 0
        else:
            draw = False
        
        # Break if we reach time limit without evacuation
        if t >= Tf:
            if verbose:
                print(f"Simulation reached time limit {Tf} with {total_people} people remaining")
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
        
        # Store results
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
    population_sizes = [10, 20, 50, 75, 100, 150, 200]
    
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
