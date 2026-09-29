# NEERAKSH Mobile Working Prototype

This mobile app follows the workflow shown in the NEERAKSH SIH PPT:

Sign In → Select Dam → Dam Details → Scenario Generation → Simulation → Flood Map → Impact Analysis → Model Comparison → GIS Export.

## It is a prototype, not the complete final model.

### Real data/output used

The app reads from the existing NEERAKSH-1 FastAPI backend:

- Official Mettur metadata
- Tamil Nadu Agriculture reservoir observation
- Completed Mettur HLL result
- Actual maximum-depth GeoTIFF
- Actual maximum-velocity GeoTIFF
- Actual arrival-time GeoTIFF

### No fake values

The app does not create:

- a verified breach location
- an actual Mettur failure prediction
- SPH result values
- Delft3D result values
- population affected
- village/road/building counts

Those are shown as pending until actual datasets/model outputs are connected.

## 1. Put the mobile app inside the current project

Copy this `mobile` folder into:

C:\NEERAKSH-1\mobile

## 2. Configure the API address

Open:

mobile\App.tsx

Find:

const API_BASE_URL = "http://10.0.2.2:8000";

For a physical Android phone connected to the same Wi-Fi as the PC, change it to your PC IPv4 address, for example:

const API_BASE_URL = "http://192.168.1.5:8000";

Do not use `localhost` on a physical phone.

## 3. Start the existing FastAPI backend

Use the backend that serves:

/api/dam/mettur
/api/scenarios/mettur
/api/results/mettur
/api/layer/{layer}/metadata
/api/layer/{layer}.png

If using the prototype backend supplied with this project:

uvicorn prototype.backend.main:app --reload --host 0.0.0.0 --port 8000

## 4. Start Expo

cd C:\NEERAKSH-1\mobile

npm install

npx expo start

Then:

- Scan the QR code with Expo Go on Android, or
- Press `a` for Android emulator.

## 5. Prototype flow

Login
→ Dashboard
→ Mettur Dam
→ Scenario Generation
→ METTUR_SCREENING_BASE
→ View Completed HLL Result
→ Flood Map
→ Depth / Velocity / Arrival
→ Impact Analysis
→ Model Comparison
→ GIS Export

The BASE scenario is the only scenario with a completed HLL result. LOW/HIGH do not display invented results.
