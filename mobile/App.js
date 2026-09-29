import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  View,
} from "react-native";
import * as Location from "expo-location";
import MapView, { Marker } from "react-native-maps";

const API_URL = "http://172.20.10.3:8000";

const COLORS = {
  saffron: "#FF8C00",
  green: "#138A45",
  darkGreen: "#075C2D",
  white: "#FFFFFF",
  black: "#17251D",
  grey: "#68756E",
  light: "#EEF5F0",
  border: "#DDE7E0",
  red: "#C62828",
};

export default function App() {
  const [role, setRole] = useState(null);
  const [screen, setScreen] = useState("home");

  const [dams, setDams] = useState([]);
  const [selectedDam, setSelectedDam] = useState(null);

  const [weather, setWeather] = useState(null);
  const [location, setLocation] = useState(null);

  const [simulation, setSimulation] = useState(null);
  const [loading, setLoading] = useState(false);

  // =========================================================
  // LOAD DAMS
  // =========================================================

  async function loadDams() {
    try {
      const response = await fetch(`${API_URL}/api/dams`);

      if (!response.ok) {
        throw new Error("Dam API failed");
      }

      const data = await response.json();

      /*
        Backend may return:
        { dams: [...] }
        OR
        [...]
        OR
        { data: [...] }

        Normalize everything into an array.
      */

      const rawDams = Array.isArray(data)
        ? data
        : Array.isArray(data.dams)
        ? data.dams
        : Array.isArray(data.data)
        ? data.data
        : [];

      const normalizedDams = rawDams.map((dam) => ({
        ...dam,

        // Backend uses lat/lng.
        // Mobile app uses latitude/longitude.
        latitude: dam.latitude ?? dam.lat,
        longitude: dam.longitude ?? dam.lng,
      }));

      setDams(normalizedDams);

      if (normalizedDams.length > 0) {
        setSelectedDam(normalizedDams[0]);
      } else {
        Alert.alert(
          "No dams returned",
          "The NEERAKSH backend did not return any dam records."
        );
      }
    } catch (error) {
      console.log("LOAD DAMS ERROR:", error);

      Alert.alert(
        "Backend unavailable",
        "Start the NEERAKSH FastAPI backend and make sure your phone and computer are on the same network."
      );
    }
  }

  // =========================================================
  // LOAD WEATHER
  // =========================================================

  async function loadWeather(dam) {
    if (!dam) return;

    const latitude = dam.latitude ?? dam.lat;
    const longitude = dam.longitude ?? dam.lng;

    if (latitude == null || longitude == null) {
      console.log("No coordinates for dam");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(
        `${API_URL}/api/weather?latitude=${latitude}&longitude=${longitude}`
      );

      if (!response.ok) {
        throw new Error("Weather request failed");
      }

      const data = await response.json();

      setWeather(data);
    } catch (error) {
      console.log("WEATHER ERROR:", error);

      Alert.alert(
        "Weather error",
        "Could not retrieve live weather data."
      );
    } finally {
      setLoading(false);
    }
  }

  // =========================================================
  // LOCATION
  // =========================================================

  async function requestLocation() {
    try {
      const { status } =
        await Location.requestForegroundPermissionsAsync();

      if (status !== "granted") {
        return;
      }

      const position =
        await Location.getCurrentPositionAsync({
          accuracy: Location.Accuracy.Balanced,
        });

      setLocation({
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
      });
    } catch (error) {
      console.log("LOCATION ERROR:", error);
    }
  }

  // =========================================================
  // REAL GOVERNMENT CASE-STUDY SIMULATION
  // =========================================================

  async function startSimulation() {
    if (!selectedDam) {
      Alert.alert("Select dam", "Please select a dam first.");
      return;
    }

    setLoading(true);
    setSimulation(null);

    try {
      /*
        IMPORTANT:
        Current backend endpoint is GET.

        Example:
        /api/simulation/varattupallam
      */

      const response = await fetch(
        `${API_URL}/api/simulation/${selectedDam.id}`
      );

      const data = await response.json();

      if (!response.ok) {
        Alert.alert(
          "Simulation not available",
          data.detail ||
            "A government-published hydraulic case is not configured for this dam."
        );

        return;
      }

      console.log("SIMULATION RESULT:", data);

      setSimulation(data);
      setScreen("simulation");
    } catch (error) {
      console.log("SIMULATION ERROR:", error);

      Alert.alert(
        "Backend unavailable",
        "Cannot connect to NEERAKSH backend."
      );
    } finally {
      setLoading(false);
    }
  }

  // =========================================================
  // INITIAL LOAD
  // =========================================================

  useEffect(() => {
    loadDams();
    requestLocation();
  }, []);

  // =========================================================
  // WEATHER WHEN DAM CHANGES
  // =========================================================

  useEffect(() => {
    if (selectedDam) {
      loadWeather(selectedDam);
    }
  }, [selectedDam]);

  // =========================================================
  // ROLE SCREEN
  // =========================================================

  if (!role) {
    return (
      <RoleScreen
        setRole={(value) => {
          setRole(value);
          setScreen("home");
        }}
      />
    );
  }

  // =========================================================
  // MAIN APP
  // =========================================================

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar
        barStyle="dark-content"
        backgroundColor="#FFFFFF"
      />

      <Header
        role={role}
        onChangeRole={() => {
          setRole(null);
          setScreen("home");
        }}
      />

      {screen === "home" && (
        <HomeScreen
          role={role}
          dams={dams}
          selectedDam={selectedDam}
          setSelectedDam={setSelectedDam}
          weather={weather}
          location={location}
          loading={loading}
          onSimulation={startSimulation}
          onNavigate={setScreen}
        />
      )}

      {screen === "simulation" && (
        <SimulationScreen
          simulation={simulation}
          dam={selectedDam}
          onBack={() => setScreen("home")}
        />
      )}

      {screen === "alerts" && (
        <AlertsScreen
          role={role}
          dam={selectedDam}
          weather={weather}
        />
      )}

      {screen === "impact" && (
        <ImpactScreen
          role={role}
          dam={selectedDam}
          simulation={simulation}
        />
      )}

      <BottomNavigation
        screen={screen}
        setScreen={setScreen}
      />
    </SafeAreaView>
  );
}

// =========================================================
// ROLE SCREEN
// =========================================================

function RoleScreen({ setRole }) {
  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar
        barStyle="dark-content"
        backgroundColor="#FFFFFF"
      />

      <View style={styles.tricolor}>
        <View
          style={{
            flex: 1,
            backgroundColor: COLORS.saffron,
          }}
        />

        <View
          style={{
            flex: 1,
            backgroundColor: COLORS.white,
          }}
        />

        <View
          style={{
            flex: 1,
            backgroundColor: COLORS.green,
          }}
        />
      </View>

      <View style={styles.roleContainer}>
        <View style={styles.logo}>
          <Text style={styles.logoWater}>≈</Text>
        </View>

        <Text style={styles.brand}>
          NEERAKSH
        </Text>

        <Text style={styles.tagline}>
          Dam Break & Flood Intelligence
        </Text>

        <View style={styles.divider} />

        <Text style={styles.chooseTitle}>
          Select access mode
        </Text>

        <Text style={styles.chooseSubtitle}>
          No credentials required for this demonstration
        </Text>

        <Pressable
          style={styles.roleCard}
          onPress={() => setRole("civilian")}
        >
          <View
            style={[
              styles.roleIcon,
              { backgroundColor: "#EAF7EF" },
            ]}
          >
            <Text style={styles.roleEmoji}>👤</Text>
          </View>

          <View style={{ flex: 1 }}>
            <Text style={styles.roleTitle}>
              Civilian
            </Text>

            <Text style={styles.roleText}>
              Flood information, alerts, affected
              zones and evacuation information.
            </Text>
          </View>

          <Text style={styles.arrow}>›</Text>
        </Pressable>

        <Pressable
          style={styles.roleCard}
          onPress={() => setRole("authority")}
        >
          <View
            style={[
              styles.roleIcon,
              { backgroundColor: "#FFF3E3" },
            ]}
          >
            <Text style={styles.roleEmoji}>🛡</Text>
          </View>

          <View style={{ flex: 1 }}>
            <Text style={styles.roleTitle}>
              Authority
            </Text>

            <Text style={styles.roleText}>
              Dam monitoring, simulation, impact
              assessment and emergency alerts.
            </Text>
          </View>

          <Text style={styles.arrow}>›</Text>
        </Pressable>

        <Text style={styles.footer}>
          SIH 2026 • NEERAKSH
        </Text>
      </View>
    </SafeAreaView>
  );
}

// =========================================================
// HEADER
// =========================================================

function Header({ role, onChangeRole }) {
  return (
    <View style={styles.header}>
      <View>
        <Text style={styles.headerBrand}>
          NEERAKSH
        </Text>

        <Text style={styles.headerSub}>
          {role === "authority"
            ? "AUTHORITY MODE"
            : "CIVILIAN MODE"}
        </Text>
      </View>

      <Pressable onPress={onChangeRole}>
        <Text style={styles.changeRole}>
          Change
        </Text>
      </Pressable>
    </View>
  );
}

// =========================================================
// HOME
// =========================================================

function HomeScreen({
  role,
  dams,
  selectedDam,
  setSelectedDam,
  weather,
  location,
  loading,
  onSimulation,
  onNavigate,
}) {
  return (
    <ScrollView
      contentContainerStyle={styles.content}
    >
      <Text style={styles.sectionLabel}>
        {role === "authority"
          ? "AUTHORITY COMMAND"
          : "PUBLIC SAFETY"}
      </Text>

      <Text style={styles.pageTitle}>
        Flood Intelligence
      </Text>

      <Text style={styles.pageSubtitle}>
        Real observations and government case-study
        model outputs
      </Text>

      <Text style={styles.cardHeading}>
        Select monitored dam
      </Text>

      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
      >
        {Array.isArray(dams) &&
          dams.map((dam) => (
            <Pressable
              key={dam.id}
              onPress={() => setSelectedDam(dam)}
              style={[
                styles.damChip,
                selectedDam?.id === dam.id &&
                  styles.damChipActive,
              ]}
            >
              <Text
                style={[
                  styles.damChipText,
                  selectedDam?.id === dam.id &&
                    styles.damChipTextActive,
                ]}
              >
                {dam.name}
              </Text>
            </Pressable>
          ))}
      </ScrollView>

      {!selectedDam && (
        <View style={styles.warningCard}>
          <Text style={styles.warningTitle}>
            NO DAM DATA
          </Text>

          <Text style={styles.warningText}>
            Waiting for dam records from the NEERAKSH
            backend.
          </Text>
        </View>
      )}

      {selectedDam && (
        <>
          <View style={styles.mapContainer}>
            <MapView
              style={styles.map}
              region={{
                latitude:
                  selectedDam.latitude ??
                  selectedDam.lat ??
                  11.679444,

                longitude:
                  selectedDam.longitude ??
                  selectedDam.lng ??
                  77.567222,

                latitudeDelta: 0.18,
                longitudeDelta: 0.18,
              }}
            >
              <Marker
                coordinate={{
                  latitude:
                    selectedDam.latitude ??
                    selectedDam.lat ??
                    11.679444,

                  longitude:
                    selectedDam.longitude ??
                    selectedDam.lng ??
                    77.567222,
                }}
                title={selectedDam.name}
                description={selectedDam.river}
              />

              {location && (
                <Marker
                  coordinate={location}
                  title="Your location"
                  pinColor={COLORS.saffron}
                />
              )}
            </MapView>
          </View>

          <View style={styles.infoCard}>
            <Text style={styles.cardHeading}>
              {selectedDam.name}
            </Text>

            <Text style={styles.cardText}>
              {selectedDam.river}
            </Text>

            <Text style={styles.cardText}>
              {selectedDam.district},{" "}
              {selectedDam.state}
            </Text>
          </View>

          <Text style={styles.cardHeading}>
            Live observation
          </Text>

          <View style={styles.metrics}>
            <Metric
              title="Rainfall"
              value={
                weather?.current
                  ? `${weather.current.rain} mm`
                  : "Loading"
              }
            />

            <Metric
              title="Precipitation"
              value={
                weather?.current
                  ? `${weather.current.precipitation} mm`
                  : "Loading"
              }
            />

            <Metric
              title="Wind"
              value={
                weather?.current
                  ? `${weather.current.wind_speed} km/h`
                  : "Loading"
              }
            />

            <Metric
              title="Observed at"
              value={
                weather?.current?.time ||
                "Loading"
              }
            />
          </View>

          <View style={styles.warningCard}>
            <Text style={styles.warningTitle}>
              DATA STATUS
            </Text>

            <Text style={styles.warningText}>
              Weather values are retrieved from the
              live weather service. NEERAKSH does not
              generate synthetic rainfall values.
            </Text>
          </View>

          <Pressable
            style={styles.primaryButton}
            onPress={onSimulation}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="white" />
            ) : (
              <Text style={styles.buttonText}>
                Run Dam-Break Case Study
              </Text>
            )}
          </Pressable>

          <View style={styles.twoColumn}>
            <Pressable
              style={styles.actionCard}
              onPress={() => onNavigate("impact")}
            >
              <Text style={styles.actionTitle}>
                Impact
              </Text>

              <Text style={styles.actionText}>
                View available model outputs
              </Text>
            </Pressable>

            <Pressable
              style={styles.actionCard}
              onPress={() => onNavigate("alerts")}
            >
              <Text style={styles.actionTitle}>
                Alerts
              </Text>

              <Text style={styles.actionText}>
                Emergency communication
              </Text>
            </Pressable>
          </View>
        </>
      )}
    </ScrollView>
  );
}

// =========================================================
// SIMULATION SCREEN
// =========================================================

function SimulationScreen({
  simulation,
  dam,
  onBack,
}) {
  if (!simulation) {
    return (
      <View style={styles.center}>
        <Text>
          No simulation result available.
        </Text>
      </View>
    );
  }

  const overtopping =
    simulation.scenarios?.overtopping;

  const piping =
    simulation.scenarios?.piping;

  const downstream =
    Array.isArray(simulation.downstream)
      ? simulation.downstream
      : [];

  return (
    <ScrollView
      contentContainerStyle={styles.content}
    >
      <Pressable onPress={onBack}>
        <Text style={styles.back}>
          ‹ Back
        </Text>
      </Pressable>

      <Text style={styles.sectionLabel}>
        GOVERNMENT CASE STUDY
      </Text>

      <Text style={styles.pageTitle}>
        {dam?.name || "Varattupallam Dam"}
      </Text>

      <Text style={styles.pageSubtitle}>
        Published hydraulic dam-break case-study
        outputs received from NEERAKSH backend
      </Text>

      <View style={styles.resultCard}>
        <Text style={styles.cardHeading}>
          Simulation status
        </Text>

        <Text style={styles.resultStatus}>
          {simulation.status}
        </Text>

        <Text style={styles.cardText}>
          {simulation.message}
        </Text>
      </View>

      {overtopping && (
        <View style={styles.resultCard}>
          <Text style={styles.cardHeading}>
            Overtopping scenario
          </Text>

          <Metric
            title="Breach width"
            value={`${overtopping.breach_width_m} m`}
          />

          <Metric
            title="Formation time"
            value={`${overtopping.formation_time_hr} hr`}
          />

          <Metric
            title="Peak discharge"
            value={`${overtopping.peak_discharge_m3s} m³/s`}
          />

          <Metric
            title="Side slope"
            value={overtopping.side_slope}
          />
        </View>
      )}

      {piping && (
        <View style={styles.resultCard}>
          <Text style={styles.cardHeading}>
            Piping scenario
          </Text>

          <Metric
            title="Breach width"
            value={`${piping.breach_width_m} m`}
          />

          <Metric
            title="Formation time"
            value={`${piping.formation_time_hr} hr`}
          />

          <Metric
            title="Peak discharge"
            value={`${piping.peak_discharge_m3s} m³/s`}
          />

          <Metric
            title="Side slope"
            value={piping.side_slope}
          />
        </View>
      )}

      {downstream.length > 0 && (
        <View style={styles.resultCard}>
          <Text style={styles.cardHeading}>
            Downstream discharge
          </Text>

          {downstream.map((point, index) => (
            <View
              key={`${point.location}-${index}`}
              style={styles.downstreamRow}
            >
              <Text style={styles.downstreamName}>
                {point.location}
              </Text>

              <Text style={styles.downstreamText}>
                {point.distance_km} km
              </Text>

              <Text style={styles.downstreamText}>
                OT: {point.overtopping_m3s} m³/s
              </Text>

              <Text style={styles.downstreamText}>
                Piping: {point.piping_m3s} m³/s
              </Text>
            </View>
          ))}
        </View>
      )}

      <View style={styles.warningCard}>
        <Text style={styles.warningTitle}>
          IMPORTANT
        </Text>

        <Text style={styles.warningText}>
          These values are published case-study
          results. They are not presented as a
          live prediction of a future dam failure.
        </Text>
      </View>

      <View style={styles.resultCard}>
        <Text style={styles.cardHeading}>
          Official sources
        </Text>

        <Text style={styles.cardText}>
          CWC National Register of Large Dams
        </Text>

        <Text style={styles.cardText}>
          CWC dam-break case study
        </Text>
      </View>
    </ScrollView>
  );
}

// =========================================================
// IMPACT
// =========================================================

function ImpactScreen({
  role,
  dam,
  simulation,
}) {
  return (
    <ScrollView
      contentContainerStyle={styles.content}
    >
      <Text style={styles.sectionLabel}>
        IMPACT ASSESSMENT
      </Text>

      <Text style={styles.pageTitle}>
        Downstream Impact
      </Text>

      <Text style={styles.pageSubtitle}>
        Results are populated only from available
        model outputs.
      </Text>

      <View style={styles.resultCard}>
        <Text style={styles.cardHeading}>
          Current case
        </Text>

        <Text style={styles.cardText}>
          Dam: {dam?.name || "Not selected"}
        </Text>

        <Text style={styles.cardText}>
          Role: {role}
        </Text>

        <Text style={styles.cardText}>
          Status:{" "}
          {simulation?.status ||
            "No simulation executed"}
        </Text>
      </View>

      {!simulation && (
        <View style={styles.warningCard}>
          <Text style={styles.warningTitle}>
            NO MODEL OUTPUT
          </Text>

          <Text style={styles.warningText}>
            NEERAKSH will not display invented
            population, depth, velocity or
            inundation values.
          </Text>
        </View>
      )}

      {simulation?.downstream &&
        Array.isArray(simulation.downstream) && (
          <View style={styles.resultCard}>
            <Text style={styles.cardHeading}>
              Available downstream discharge
            </Text>

            {simulation.downstream.map(
              (point, index) => (
                <View
                  key={`${point.location}-${index}`}
                  style={styles.downstreamRow}
                >
                  <Text style={styles.downstreamName}>
                    {point.location}
                  </Text>

                  <Text style={styles.downstreamText}>
                    Distance: {point.distance_km} km
                  </Text>

                  <Text style={styles.downstreamText}>
                    Overtopping:{" "}
                    {point.overtopping_m3s} m³/s
                  </Text>

                  <Text style={styles.downstreamText}>
                    Piping:{" "}
                    {point.piping_m3s} m³/s
                  </Text>
                </View>
              )
            )}
          </View>
        )}
    </ScrollView>
  );
}

// =========================================================
// ALERTS
// =========================================================

function AlertsScreen({
  role,
  dam,
  weather,
}) {
  return (
    <ScrollView
      contentContainerStyle={styles.content}
    >
      <Text style={styles.sectionLabel}>
        {role === "authority"
          ? "AUTHORITY ALERTING"
          : "SAFETY ALERTS"}
      </Text>

      <Text style={styles.pageTitle}>
        Emergency Communication
      </Text>

      <View style={styles.resultCard}>
        <Text style={styles.cardHeading}>
          Monitoring
        </Text>

        <Text style={styles.cardText}>
          {dam?.name || "No dam selected"}
        </Text>

        <Text style={styles.cardText}>
          Live rainfall:{" "}
          {weather?.current
            ? `${weather.current.rain} mm`
            : "Unavailable"}
        </Text>
      </View>

      <View style={styles.warningCard}>
        <Text style={styles.warningTitle}>
          ALERT POLICY
        </Text>

        <Text style={styles.warningText}>
          NEERAKSH does not create a warning from
          arbitrary numbers. Emergency alerts will
          be generated only after validated
          observations and configured authority
          thresholds are available.
        </Text>
      </View>
    </ScrollView>
  );
}

// =========================================================
// METRIC
// =========================================================

function Metric({ title, value }) {
  return (
    <View style={styles.metric}>
      <Text style={styles.metricTitle}>
        {title}
      </Text>

      <Text style={styles.metricValue}>
        {value}
      </Text>
    </View>
  );
}

// =========================================================
// BOTTOM NAVIGATION
// =========================================================

function BottomNavigation({
  screen,
  setScreen,
}) {
  return (
    <View style={styles.bottom}>
      <Pressable
        onPress={() => setScreen("home")}
        style={styles.bottomItem}
      >
        <Text
          style={[
            styles.bottomText,
            screen === "home" &&
              styles.bottomActive,
          ]}
        >
          HOME
        </Text>
      </Pressable>

      <Pressable
        onPress={() => setScreen("simulation")}
        style={styles.bottomItem}
      >
        <Text
          style={[
            styles.bottomText,
            screen === "simulation" &&
              styles.bottomActive,
          ]}
        >
          SIMULATION
        </Text>
      </Pressable>

      <Pressable
        onPress={() => setScreen("impact")}
        style={styles.bottomItem}
      >
        <Text
          style={[
            styles.bottomText,
            screen === "impact" &&
              styles.bottomActive,
          ]}
        >
          IMPACT
        </Text>
      </Pressable>

      <Pressable
        onPress={() => setScreen("alerts")}
        style={styles.bottomItem}
      >
        <Text
          style={[
            styles.bottomText,
            screen === "alerts" &&
              styles.bottomActive,
          ]}
        >
          ALERTS
        </Text>
      </Pressable>
    </View>
  );
}

// =========================================================
// STYLES
// =========================================================

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: COLORS.white,
  },

  tricolor: {
    height: 7,
    flexDirection: "row",
  },

  roleContainer: {
    flex: 1,
    padding: 24,
    justifyContent: "center",
    alignItems: "center",
  },

  logo: {
    width: 76,
    height: 76,
    borderRadius: 24,
    backgroundColor: COLORS.green,
    justifyContent: "center",
    alignItems: "center",
    borderTopWidth: 6,
    borderTopColor: COLORS.saffron,
  },

  logoWater: {
    color: COLORS.white,
    fontSize: 48,
    fontWeight: "900",
  },

  brand: {
    marginTop: 16,
    fontSize: 34,
    fontWeight: "900",
    letterSpacing: 4,
    color: COLORS.black,
  },

  tagline: {
    marginTop: 5,
    color: COLORS.grey,
    fontSize: 13,
  },

  divider: {
    width: 60,
    height: 3,
    backgroundColor: COLORS.saffron,
    marginVertical: 25,
  },

  chooseTitle: {
    fontSize: 20,
    fontWeight: "900",
    color: COLORS.black,
  },

  chooseSubtitle: {
    color: COLORS.grey,
    fontSize: 11,
    marginTop: 5,
    marginBottom: 18,
  },

  roleCard: {
    width: "100%",
    minHeight: 105,
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 18,
    padding: 15,
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 12,
    gap: 13,
  },

  roleIcon: {
    width: 54,
    height: 54,
    borderRadius: 16,
    justifyContent: "center",
    alignItems: "center",
  },

  roleEmoji: {
    fontSize: 25,
  },

  roleTitle: {
    fontSize: 16,
    fontWeight: "900",
    color: COLORS.black,
  },

  roleText: {
    fontSize: 11,
    color: COLORS.grey,
    lineHeight: 17,
    marginTop: 4,
  },

  arrow: {
    fontSize: 28,
    color: COLORS.grey,
  },

  footer: {
    marginTop: 18,
    color: COLORS.grey,
    fontSize: 10,
  },

  header: {
    height: 65,
    paddingHorizontal: 17,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.border,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },

  headerBrand: {
    fontSize: 20,
    fontWeight: "900",
    letterSpacing: 2,
    color: COLORS.black,
  },

  headerSub: {
    fontSize: 8,
    color: COLORS.green,
    fontWeight: "900",
    marginTop: 2,
  },

  changeRole: {
    color: COLORS.green,
    fontSize: 12,
    fontWeight: "800",
  },

  content: {
    padding: 17,
    paddingBottom: 100,
  },

  sectionLabel: {
    fontSize: 9,
    color: COLORS.green,
    fontWeight: "900",
    letterSpacing: 1.4,
    marginBottom: 5,
  },

  pageTitle: {
    fontSize: 26,
    fontWeight: "900",
    color: COLORS.black,
  },

  pageSubtitle: {
    color: COLORS.grey,
    fontSize: 12,
    marginTop: 5,
    marginBottom: 18,
  },

  cardHeading: {
    fontSize: 14,
    fontWeight: "900",
    color: COLORS.black,
    marginBottom: 8,
  },

  cardText: {
    color: COLORS.grey,
    fontSize: 11,
    lineHeight: 18,
  },

  damChip: {
    borderWidth: 1,
    borderColor: COLORS.border,
    paddingHorizontal: 13,
    paddingVertical: 9,
    borderRadius: 18,
    marginRight: 8,
    marginBottom: 14,
  },

  damChipActive: {
    backgroundColor: COLORS.light,
    borderColor: COLORS.green,
  },

  damChipText: {
    color: COLORS.grey,
    fontSize: 11,
    fontWeight: "700",
  },

  damChipTextActive: {
    color: COLORS.green,
  },

  mapContainer: {
    height: 270,
    overflow: "hidden",
    borderRadius: 18,
    borderWidth: 1,
    borderColor: COLORS.border,
    marginBottom: 12,
  },

  map: {
    flex: 1,
  },

  infoCard: {
    padding: 15,
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 16,
    marginBottom: 14,
  },

  metrics: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 9,
    marginBottom: 13,
  },

  metric: {
    width: "48%",
    padding: 13,
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 15,
    marginBottom: 9,
  },

  metricTitle: {
    fontSize: 9,
    color: COLORS.grey,
    fontWeight: "700",
  },

  metricValue: {
    fontSize: 17,
    fontWeight: "900",
    color: COLORS.green,
    marginTop: 6,
  },

  warningCard: {
    padding: 15,
    borderRadius: 16,
    backgroundColor: "#FFF7E8",
    borderWidth: 1,
    borderColor: "#F3D29D",
    marginBottom: 13,
  },

  warningTitle: {
    color: COLORS.saffron,
    fontSize: 11,
    fontWeight: "900",
    marginBottom: 5,
  },

  warningText: {
    color: COLORS.black,
    fontSize: 11,
    lineHeight: 17,
  },

  primaryButton: {
    height: 53,
    borderRadius: 15,
    backgroundColor: COLORS.green,
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 13,
  },

  buttonText: {
    color: COLORS.white,
    fontSize: 14,
    fontWeight: "900",
  },

  twoColumn: {
    flexDirection: "row",
    gap: 9,
  },

  actionCard: {
    flex: 1,
    minHeight: 95,
    padding: 14,
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 16,
  },

  actionTitle: {
    fontWeight: "900",
    color: COLORS.black,
    fontSize: 13,
  },

  actionText: {
    fontSize: 10,
    color: COLORS.grey,
    marginTop: 7,
    lineHeight: 15,
  },

  resultCard: {
    padding: 17,
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 18,
    marginBottom: 13,
  },

  resultStatus: {
    fontSize: 19,
    fontWeight: "900",
    color: COLORS.green,
    marginBottom: 7,
  },

  downstreamRow: {
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.border,
  },

  downstreamName: {
    fontSize: 13,
    fontWeight: "900",
    color: COLORS.black,
    marginBottom: 4,
  },

  downstreamText: {
    fontSize: 11,
    color: COLORS.grey,
    lineHeight: 18,
  },

  back: {
    color: COLORS.green,
    fontWeight: "900",
    marginBottom: 16,
  },

  bottom: {
    height: 70,
    borderTopWidth: 1,
    borderTopColor: COLORS.border,
    backgroundColor: COLORS.white,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-around",
  },

  bottomItem: {
    flex: 1,
    alignItems: "center",
  },

  bottomText: {
    fontSize: 9,
    color: COLORS.grey,
    fontWeight: "800",
  },

  bottomActive: {
    color: COLORS.green,
  },

  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
});