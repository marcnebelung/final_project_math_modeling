# Comprehensive Documentation: Crowd Dynamics Evacuation Simulation

## Table of Contents

1. [Introduction](#introduction)
2. [Mathematical Model](#mathematical-model)
3. [Implementation Details](#implementation-details)
4. [Code Architecture](#code-architecture)
5. [Parameter Descriptions](#parameter-descriptions)
6. [Simulation Workflow](#simulation-workflow)
7. [Metrics and Analysis](#metrics-and-analysis)
8. [Visualization](#visualization)
9. [Troubleshooting](#troubleshooting)
10. [References](#references)

---

## Introduction

This project implements a microscopic pedestrian dynamics simulation for studying evacuation scenarios. The simulation models individual pedestrians as agents that interact through social forces, following the Social Force Model framework.

### Purpose

The simulation is designed to:
- Study how various parameters affect evacuation efficiency
- Analyze crowd behavior during emergency evacuations
- Provide quantitative metrics for evacuation performance
- Enable parameter optimization for building design

### Scope

The simulation focuses on:
- Single-room evacuation scenarios
- Single exit configurations
- Homogeneous pedestrian populations (with some variation in speed and size)
- Social force interactions

---

## Mathematical Model

### Social Force Model Overview

The Social Force Model, developed by Helbing and Molnár (1995), describes pedestrian motion as resulting from a combination of:
1. A driving force toward a destination
2. Repulsive forces from other pedestrians
3. Repulsive forces from walls and obstacles

### Core Equations

#### 1. Velocity Update Equation

The velocity of each pedestrian is updated according to:

\[
\mathbf{u}(t + \Delta t) = \Delta t \frac{\mathbf{v}_d - \mathbf{u}_{old}}{\tau} + \mathbf{u}_{old} + \Delta t \frac{\mathbf{F}_{total}}{m}
\]

**Components:**
- **Relaxation term**: \(\Delta t \frac{\mathbf{v}_d - \mathbf{u}_{old}}{\tau}\)
  - Drives velocity toward desired velocity
  - \(\tau\) (relaxation time) controls response speed
  
- **Inertia term**: \(\mathbf{u}_{old}\)
  - Maintains current velocity
  
- **Force term**: \(\Delta t \frac{\mathbf{F}_{total}}{m}\)
  - Accelerates due to social forces
  - \(m\) = pedestrian mass (80 kg)

#### 2. Desired Velocity

The desired velocity points toward the exit:

\[
\mathbf{v}_d = v_0 \frac{\mathbf{r}_{exit} - \mathbf{r}_i}{|\mathbf{r}_{exit} - \mathbf{r}_i|}
\]

Where:
- \(v_0\) = desired speed (m/s)
- \(\mathbf{r}_{exit}\) = exit position
- \(\mathbf{r}_i\) = pedestrian position

#### 3. Pedestrian-Pedestrian Repulsion

\[
\mathbf{F}_{ij} = F \exp\left(-\frac{d_{ij} - (r_i + r_j)}{\delta}\right) \mathbf{n}_{ij}
\]

Where:
- \(F\) = repulsion strength (N)
- \(d_{ij}\) = distance between pedestrian centers
- \(r_i, r_j\) = pedestrian radii
- \(\delta\) = interaction range (0.08 m)
- \(\mathbf{n}_{ij}\) = normalized direction from \(j\) to \(i\)

**Physical Interpretation:**
- Exponential decay with distance
- Strong repulsion when pedestrians are close
- Negligible interaction beyond ~0.3 m

#### 4. Pedestrian-Wall Repulsion

\[
\mathbf{F}_{iw} = F \exp\left(-\frac{d_{iw} - r_i}{\delta}\right) \mathbf{n}_{iw}
\]

Where:
- \(d_{iw}\) = distance from pedestrian center to wall
- \(\mathbf{n}_{iw}\) = normalized direction from wall to pedestrian

#### 5. Contact Forces (Overlap Correction)

When pedestrians overlap (\(d_{ij} < r_i + r_j\)):

\[
\mathbf{F}_{contact} = \kappa (r_i + r_j - d_{ij}) \mathbf{n}_{ij} - \eta \Delta v_{ij}
\]

Where:
- \(\kappa\) = stiffness constant (120,000 N/m)
- \(\eta\) = friction coefficient (240,000 N·s/m)
- \(\Delta v_{ij}\) = relative velocity

### Model Parameters

| Symbol | Parameter | Typical Value | Physical Meaning |
|--------|-----------|---------------|------------------|
| \(v_0\) | Desired speed | 1.2 m/s | Preferred walking speed |
| \(F\) | Repulsion strength | 2000 N | Strength of social forces |
| \(\tau\) | Relaxation time | 0.5 s | Time to adjust velocity |
| \(\delta\) | Interaction range | 0.08 m | Characteristic interaction distance |
| \(\kappa\) | Stiffness | 120,000 N/m | Overlap correction strength |
| \(\eta\) | Friction | 240,000 N·s/m | Relative velocity damping |
| \(m\) | Mass | 80 kg | Pedestrian mass |
| \(r\) | Radius | 0.4-0.6 m | Pedestrian body radius |

---

## Implementation Details

### Domain Creation

The simulation domain is a rectangular room with:
- **Dimensions**: ~34 m × ~24 m (340 × 240 pixels at 0.1 m/pixel)
- **Walls**: Top, left, and right boundaries
- **Exit**: Centered opening at bottom with configurable width
- **Destination**: Red line below exit for pathfinding

**Code Location**: `enhanced_sim/parameter_sweep_simulation.py::create_domain()`

### Pedestrian Initialization

Pedestrians are initialized:
- **Position**: Randomly distributed in a box [3.6, 36.5] × [3.6, 26.5] m
- **Radius**: Uniform distribution [0.4, 0.6] m
- **Speed**: Normal distribution with mean = desired_speed, std = 0.1 m/s
- **Destination**: All assigned to "door" exit

**Constraints**:
- Minimum distance between pedestrians: `dmin_people`
- Minimum distance to walls: `dmin_walls`
- Maximum initialization iterations: 10

### Time Integration

**Time Step**: \(\Delta t = 0.005\) s

**Integration Scheme**: Explicit Euler
1. Compute desired velocities
2. Calculate social forces
3. Update velocities
4. Move pedestrians
5. Check for destination arrival
6. Update previous velocities

### Contact Detection

Contacts are detected using:
- **Maximum interaction distance**: `dmax = 0.1` m
- **Spatial indexing**: Efficient neighbor search
- **Contact list**: Array of (i, j) pairs for interacting pedestrians

### Destination Update

Pedestrians are removed when:
- They cross the exit line (y < 3 m)
- They reach the destination area

**Code Location**: `cromosim.micro.people_update_destination()`

---

## Code Architecture

### Module Structure

```
enhanced_sim/
└── parameter_sweep_simulation.py
    ├── create_domain()          # Domain geometry
    ├── create_sensor()          # Flow measurement sensor
    ├── run_simulation()         # Single simulation
    ├── run_parameter_sweep()    # Parameter sweep
    └── plot_parameter_results() # Visualization

sim_visualisation/
├── single_simulation.py
│   └── run_single_simulation()  # Visualized simulation
└── create_animation.py
    └── create_animation_from_frames()  # MP4 generation
```

### Key Functions

#### `run_simulation()`

Main simulation loop:
1. Initialize domain and pedestrians
2. While t < Tf and people remain:
   - Compute desired velocities
   - Calculate forces
   - Update positions
   - Track metrics
3. Return metrics dictionary

**Returns**:
```python
{
    'evacuation_time': float,
    'avg_flow_rate': float,
    'avg_collision_rate': float,
    'avg_exit_density': float,
    'flow_rate': [(t, rate), ...],
    'collision_count': [(t, count), ...],
    'exit_density': [(t, density), ...]
}
```

#### `run_parameter_sweep()`

Systematic parameter exploration:
1. For each parameter in ranges:
   - For each parameter value:
     - Run N repetitions with different seeds
     - Aggregate statistics (mean, std)
   - Store results
2. Return results dictionary

**Structure**:
```python
{
    'param_name': {
        value: {
            'evacuation_time': {'mean': float, 'std': float},
            'flow_rate': {'mean': float, 'std': float},
            ...
        }
    }
}
```

---

## Parameter Descriptions

### Tunable Parameters

#### 1. Number of People (`num_people`)

- **Range**: 1-200
- **Effect**: 
  - More people → longer evacuation time (non-linear)
  - Higher density → more collisions
  - Can cause congestion at exit
- **Typical Values**: 10, 25, 50, 75, 100

#### 2. Desired Speed (`desired_speed`)

- **Range**: 0.5-5.0 m/s
- **Effect**:
  - Higher speed → faster evacuation (up to a point)
  - Very high speed → more collisions
  - Realistic range: 1.0-1.5 m/s
- **Typical Values**: 1.0, 1.2, 1.5, 2.0 m/s

#### 3. Repulsion Strength (`repulsion_strength`)

- **Range**: 100-5000 N
- **Effect**:
  - Higher F → stronger avoidance
  - Too high → unrealistic behavior
  - Too low → frequent collisions
- **Typical Values**: 1000, 2000, 3000, 5000 N

#### 4. Relaxation Time (`relaxation_time`)

- **Range**: 0.1-5.0 s
- **Effect**:
  - Lower τ → faster response to obstacles
  - Higher τ → smoother motion, slower response
  - Affects collision avoidance
- **Typical Values**: 0.1, 0.5, 1.0, 2.0 s

#### 5. Door Width (`door_width`)

- **Range**: 1.0-12.0 m
- **Effect**:
  - Wider door → higher flow rate
  - Diminishing returns beyond ~5-7 m
  - Critical for high-density scenarios
- **Typical Values**: 1.5, 2.5, 5.0, 7.5, 10.0 m

### Fixed Parameters

These are typically not varied:

- **Mass** (`mass`): 80 kg
- **Stiffness** (`kappa`): 120,000 N/m
- **Friction** (`eta`): 240,000 N·s/m
- **Interaction range** (`delta`): 0.08 m
- **Directional dependence** (`lambda_`): 0.5
- **Time step** (`dt`): 0.005 s
- **Maximum distance** (`dmax`): 0.1 m

---

## Simulation Workflow

### Step-by-Step Process

1. **Domain Setup**
   ```
   create_domain(door_width) → Domain object
   ```

2. **Pedestrian Initialization**
   ```
   people_initialization(domain, groups, dt, ...) → People dictionary
   ```

3. **Main Loop** (for each time step):
   ```
   a. Compute desired velocities
   b. Detect contacts
   c. Calculate forces
   d. Update velocities
   e. Move pedestrians
   f. Update destinations
   g. Track metrics
   ```

4. **Metrics Collection**
   - Every 1 second:
     - Count collisions
     - Calculate exit density
     - Measure flow rate

5. **Termination**
   - All pedestrians evacuated, OR
   - Maximum time reached

### Running a Simulation

**Single Simulation**:
```python
from enhanced_sim.parameter_sweep_simulation import run_simulation

metrics = run_simulation(
    num_people=50,
    desired_speed=1.2,
    repulsion_strength=2000.0,
    relaxation_time=0.5,
    door_width=5.0,
    Tf=500.0
)
```

**Parameter Sweep**:
```python
from enhanced_sim.parameter_sweep_simulation import run_parameter_sweep

ranges = {
    'num_people': [10, 25, 50, 75, 100],
    'door_width': [1.5, 2.5, 5.0, 7.5, 10.0]
}

results = run_parameter_sweep(ranges, repetitions=5)
```

---

## Metrics and Analysis

### Primary Metrics

#### 1. Evacuation Time

**Definition**: Time until all pedestrians have exited

**Calculation**: 
- Tracked when `people_count == 0`
- If not all evacuated, set to `Tf`

**Units**: seconds

**Interpretation**:
- Lower is better
- Non-linear with number of people
- Sensitive to door width

#### 2. Flow Rate

**Definition**: Number of people exiting per second

**Calculation**:
\[
\text{Flow Rate} = \frac{\text{People evacuated in interval}}{\text{Time interval}}
\]

**Units**: people/second

**Typical Values**: 1-5 people/s (depends on door width)

**Interpretation**:
- Higher is better
- Plateaus at high densities (capacity limit)
- Related to door width

#### 3. Collision Rate

**Definition**: Average number of contacts per second

**Calculation**:
- Count contacts at each metric interval
- Average over simulation

**Units**: collisions/second

**Interpretation**:
- Lower is better (smoother flow)
- Increases with density
- Affected by repulsion strength

#### 4. Exit Density

**Definition**: Average number of people per square meter near exit

**Calculation**:
\[
\text{Density} = \frac{\text{People in exit area}}{\text{Exit area size}}
\]

**Exit Area**: Rectangle around door (width + 2 m, height 3 m)

**Units**: people/m²

**Typical Values**: 0-5 people/m²

**Interpretation**:
- Moderate density → efficient flow
- Too high → congestion
- Too low → underutilized exit

### Statistical Analysis

For parameter sweeps:
- **Repetitions**: Multiple runs with different seeds
- **Statistics**: Mean and standard deviation
- **Error bars**: ±1 standard deviation

**Example Output**:
```python
{
    'evacuation_time': {
        'mean': 45.2,
        'std': 2.1
    },
    'flow_rate': {
        'mean': 2.3,
        'std': 0.15
    }
}
```

---

## Visualization

### Frame Generation

Each simulation frame shows:
- **Domain**: Room walls and exit
- **Pedestrians**: Colored circles (color = radius)
- **Sensors**: Exit flow measurement line
- **Time**: Current simulation time

**Frame Rate**: Every `drawper` iterations (default: 20)
- At dt=0.005 s, drawper=20 → ~0.1 s between frames

### Animation Creation

**Tool**: FFmpeg

**Process**:
1. Collect all frame PNG files
2. Sort by frame number
3. Generate MP4 with specified FPS

**Code**: `sim_visualisation/create_animation.py`

**Usage**:
```python
create_animation_from_frames(
    prefix="results_50p_5dw_1.2sp/",
    domain_name="room",
    fps=10  # Adjust for desired playback speed
)
```

### Parameter Sweep Plots

**Format**: 2×2 subplot grid

**Metrics Shown**:
1. Evacuation time vs. parameter
2. Flow rate vs. parameter
3. Collision rate vs. parameter
4. Exit density vs. parameter

**Features**:
- Error bars (standard deviation)
- Trend lines (polynomial fit)
- Grid for readability

---

## Troubleshooting

### Common Issues

#### 1. Import Errors

**Problem**: `ModuleNotFoundError: No module named 'cromosim'`

**Solution**:
```bash
pip install cromosim
```

If not available via pip, install from source:
```bash
git clone https://github.com/cromosim/cromosim.git
cd cromosim
pip install -e .
```

#### 2. Simulation Not Completing

**Problem**: People not evacuating

**Possible Causes**:
- Door too narrow
- Repulsion too strong
- Relaxation time too high
- Initial positions too far from exit

**Solutions**:
- Increase `door_width`
- Reduce `repulsion_strength`
- Decrease `relaxation_time`
- Check domain geometry

#### 3. High Collision Rates

**Problem**: Many collisions observed

**Solutions**:
- Increase `repulsion_strength`
- Decrease `relaxation_time`
- Reduce `num_people`
- Increase `door_width`

#### 4. Animation Not Creating

**Problem**: FFmpeg error

**Solutions**:
- Install FFmpeg: `brew install ffmpeg` (macOS)
- Check file paths
- Ensure frame files exist
- Verify FFmpeg in PATH

#### 5. Slow Performance

**Problem**: Simulations take too long

**Optimizations**:
- Reduce `num_people`
- Increase `dt` (may affect accuracy)
- Reduce `Tf` if evacuation completes early
- Increase `drawper` (fewer visualizations)

### Performance Tips

1. **For Parameter Sweeps**:
   - Use fewer repetitions for initial exploration
   - Reduce parameter range
   - Run overnight for large sweeps

2. **For Visualization**:
   - Use `drawper > 20` to reduce frame count
   - Lower resolution if needed
   - Skip visualization for parameter sweeps

3. **Memory Management**:
   - Clear old result directories
   - Don't store all frames in memory
   - Use generators for large datasets

---

## References

### Key Papers

1. **Helbing, D., & Molnár, P. (1995)**. Social force model for pedestrian dynamics. *Physical Review E*, 51(5), 4282-4286.

2. **Helbing, D., Farkas, I., & Vicsek, T. (2000)**. Simulating dynamical features of escape panic. *Nature*, 407(6803), 487-490.

3. **Helbing, D., & Johansson, A. (2009)**. Pedestrian, crowd and evacuation dynamics. *Encyclopedia of Complexity and Systems Science*, 16, 6476-6495.

### Software

- **Cromosim**: https://github.com/cromosim/cromosim
- **NumPy**: https://numpy.org/
- **Matplotlib**: https://matplotlib.org/

### Related Models

- **Optimal Velocity Model**
- **Cellular Automata Models**
- **Agent-Based Models**
- **Continuum Models**

---

## Appendix: Code Examples

### Complete Simulation Example

```python
from enhanced_sim.parameter_sweep_simulation import run_simulation

# Run simulation
metrics = run_simulation(
    num_people=50,
    desired_speed=1.2,
    repulsion_strength=2000.0,
    relaxation_time=0.5,
    door_width=5.0,
    seed=40,
    Tf=500.0,
    dt=0.005,
    verbose=True
)

# Print results
print(f"Evacuation Time: {metrics['evacuation_time']:.2f} s")
print(f"Average Flow Rate: {metrics['avg_flow_rate']:.2f} people/s")
print(f"Average Collision Rate: {metrics['avg_collision_rate']:.2f} collisions/s")
print(f"Average Exit Density: {metrics['avg_exit_density']:.2f} people/m²")
```

### Parameter Sweep Example

```python
from enhanced_sim.parameter_sweep_simulation import (
    run_parameter_sweep,
    plot_parameter_results
)

# Define parameter ranges
parameter_ranges = {
    'num_people': [10, 25, 50, 75, 100, 125, 150],
    'door_width': [1.5, 2.5, 5.0, 7.5, 10.0]
}

# Run sweep
results = run_parameter_sweep(parameter_ranges, repetitions=3)

# Save results
import json
with open('results.json', 'w') as f:
    json_results = {
        param: {str(k): v for k, v in param_results.items()}
        for param, param_results in results.items()
    }
    json.dump(json_results, f, indent=2)

# Plot results
plot_parameter_results(results)
```

---

**Last Updated**: 2024

**Version**: 1.0

**Author**: Mathematical Modeling Course Project


