# NEERAKSHA

## AI-Assisted Dam-Breach Flood Simulation and Real-Time Disaster Alerting Platform

NEERAKSHA is a disaster-management prototype designed to connect dam-breach simulation, hydrological data, geospatial processing, risk visualization, and mobile alerting into a single workflow.

The platform demonstrates how simulation-derived flood indicators can be transformed into actionable information for civilians and disaster-response authorities.

---

## Key Capabilities

- Real-time reservoir observation ingestion
- Dam-breach scenario definition
- Particle-based hydrodynamic simulation using DualSPHysics
- SPH result post-processing
- Flood depth, velocity, and arrival-time indicators
- GIS-based dam and river data processing
- Mobile flood visualization and alert interface
- Backend API for simulation and disaster information
- Scenario-based emergency analysis

---

## System Architecture

```text
Government / Hydrological Data
            |
            v
    NEERAKSHA Backend
            |
     +------+------+
     |             |
     v             v
  Breach       GIS Processing
  Scenario          |
  Engine            |
     |              |
     +------+-------+
            |
            v
     DualSPHysics 5.4
            |
            v
      SPH Simulation
            |
            v
    SPH Post-processing
            |
     +------+------+------+
     |      |      |      |
     v      v      v      |
   Depth Velocity Arrival |
              Time        |
     |      |      |      |
     +------+------+------+
            |
            v
     FastAPI Backend
            |
            v
      NEERAKSHA Mobile
            |
            v
    Risk Visualization
    & Emergency Alerts