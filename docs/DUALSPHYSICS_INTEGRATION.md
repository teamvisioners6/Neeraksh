# DualSPHysics Integration

## Overview

NEERAKSHA uses DualSPHysics 5.4 as an external particle-based
hydrodynamic simulation engine for prototype dam-breach flow analysis.

The NEERAKSHA repository contains the integration layer,
simulation definitions, and post-processing pipeline.
The complete DualSPHysics source tree and compiled binaries
are maintained separately as an external dependency.

## NEERAKSHA Simulation Workflow

Breach Definition
? DualSPHysics 5.4
? SPH Particle Output
? SPH Post-processing
? Depth / Velocity / Arrival Time
? NEERAKSHA Backend
? Mobile Visualization

## NEERAKSHA Integration Components

### Backend

- ackend/mettur_breach_solver_interface.py
- ackend/sph_postprocess.py
- ackend/main.py

### Simulation Configuration

- simulations/sph/mettur_profile/
- MetturSPH2D_BREACH50_Def.xml
- MetturSPH2D_BREACH50_out.xml

### Processed SPH Products

The repository includes lightweight simulation summaries and
post-processing metadata used by the NEERAKSHA backend.

## Prototype Demonstration

A Mettur hypothetical 50 m breach scenario was executed using
DualSPHysics 5.4 locally.

The prototype produced SPH-based indicators including:

- Maximum depth
- Maximum velocity
- Arrival time
- Final downstream propagation

These outputs are used to demonstrate the end-to-end integration
between the hydrodynamic solver and the NEERAKSHA application.

## External Solver

DualSPHysics is an external dependency and is not redistributed
as part of this repository.

The solver must be installed or maintained separately on the
machine used for running the full SPH simulation.

## Important Scientific Scope

The current DualSPHysics scenario is a prototype/hypothetical
breach-flow demonstration. Its outputs should not be interpreted
as a validated operational inundation forecast for Mettur Dam.
