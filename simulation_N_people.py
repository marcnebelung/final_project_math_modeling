import sys
import os
import json
import numpy as np
import matplotlib.pyplot as plt
from optparse import OptionParser
from cromosim.domain import Domain, Destination
from cromosim.micro import people_initialization, plot_people, plot_sensors
from cromosim.micro import find_duplicate_people, compute_contacts
from cromosim.micro import compute_forces, move_people, people_update_destination

# Experiment parameters
N_VALUES = [20, 40, 60, 80, 100]  # Population sizes to test
N_TRIALS = 5                        # Trials per population size
RESULTS = {n: [] for n in N_VALUES}

def run_simulation(input_params, N, trial):
    # seed = input_params["seed"]
    # with_graphes = input_params["with_graphes"]
    # json_domains = input_params["domains"]
    # # print("===> JSON data used to build the domains : ",json_domains)
    # json_people_init = input_params["people_init"]
    # # print("===> JSON data used to create the groups : ",json_people_init)
    # json_sensors = input_params["sensors"]
    # # print("===> JSON data used to create sensors : ",json_sensors)
    # Tf = input_params["Tf"]
    # dt = input_params["dt"]
    # drawper = input_params["drawper"]
    # mass = input_params["mass"]
    # tau = input_params["tau"]
    # F = input_params["F"]
    # kappa = input_params["kappa"]
    # delta = input_params["delta"]
    # Fwall = input_params["Fwall"]
    # lambda_ = input_params["lambda"]
    # eta = input_params["eta"]
    # projection_method = input_params["projection_method"]
    # dmax = input_params["dmax"]
    # dmin_people = input_params["dmin_people"]
    # dmin_walls = input_params["dmin_walls"]
    # plot_p = input_params["plot_people"]
    # plot_c = input_params["plot_contacts"]
    # plot_v = input_params["plot_velocities"]
    # plot_vd = input_params["plot_desired_velocities"]
    # plot_pa = input_params["plot_paths"]
    # plot_s = input_params["plot_sensors"]
    # plot_pa = input_params["plot_paths"]
    """Run single simulation instance"""
    # Initialize fresh domain
    domains = {}
    for i, jdom in enumerate(input_params["domains"]):
        # Domain initialization code from original micro_social.py
        # ... [include all original domain setup code] ...
        print(f"initialising domain {jdom}")

    # Initialize people
    all_people = {}
    for peopledom in input_params["people_init"]:
        # People initialization code from original micro_social.py
        # ... [include all people initialization code] ...
        # Modified to use current N value
        peopledom["groups"][0]["nb"] = N
        print(f"initialising group {peopledom}")

    # Run simulation
    t = 0.0
    evacuation_time = input_params["Tf"]  # Default to max time
    while t < input_params["Tf"]:
        # Original simulation loop code
        # ... [include main simulation loop] ...
        print("time {t}")
        # Check evacuation completion
        total_people = sum(p["xyrv"].shape[0] for p in all_people.values())
        if total_people == 0:
            evacuation_time = t
            break

        t += input_params["dt"]

    return evacuation_time

if __name__ == "__main__":
    # Setup
    parser = OptionParser()
    parser.add_option('--json', dest="jsonfilename", default="input_room.json",
                     type="string", help="Input json filename")
    opt, _ = parser.parse_args()

    # Load base parameters
    with open(opt.jsonfilename) as f:
        base_params = json.load(f)


    # Create output directory
    if os.path.exists("results"):
        shutil.rmtree("results")
    os.makedirs("results")

    # Run experiments
    for N in N_VALUES:
        print(f"\n=== Running N={N} ===")
        RESULTS[N] = []

        for trial in range(N_TRIALS):
            print(f" Trial {trial+1}/{N_TRIALS}")
            et = run_simulation(base_params, N, trial)
            RESULTS[N].append(et)
            print(f" Evacuation time: {et:.2f}s")

    # Plot results
    plt.figure(figsize=(10,6))
    means = [np.mean(RESULTS[n]) for n in N_VALUES]
    stds = [np.std(RESULTS[n]) for n in N_VALUES]

    plt.errorbar(N_VALUES, means, yerr=stds, fmt='-o',
                capsize=5, linewidth=2, markersize=8)
    plt.xlabel("Number of People", fontsize=12)
    plt.ylabel("Evacuation Time (s)", fontsize=12)
    plt.title("Evacuation Time vs Population Size", fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("results/evacuation_results.png", dpi=150)
    plt.show()

    # Save raw data
    np.savez("results/experiment_data.npz",
            N_VALUES=N_VALUES,
            means=means,
            stds=stds,
            all_results=RESULTS)
    """Run single simulation instance"""
