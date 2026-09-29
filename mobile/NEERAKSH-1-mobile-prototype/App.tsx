import React, { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Dimensions,
  Platform,
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import MapView, {
  Circle,
  Marker,
  Polygon,
  Polyline,
  PROVIDER_GOOGLE,
} from "react-native-maps";
import { Ionicons } from "@expo/vector-icons";

const API_BASE_URL = "http://192.168.21.210:8000";

const COLORS = {
  saffron: "#F28C28",
  saffronDark: "#C96B0A",
  green: "#138A4B",
  greenDark: "#086B38",
  white: "#FFFFFF",
  ink: "#163B2A",
  muted: "#68756E",
  bg: "#F5F7F4",
  line: "#DDE5DF",
  water: "#147E9E",
  waterLight: "#7EC9D8",
  danger: "#C94B3D",
  warning: "#E5A528",
};

const METTUR = {
  latitude: 11.7867,
  longitude: 77.8006,
};

const DAM = {
  latitude: 11.8030556,
  longitude: 77.8066667,
};

type ScreenName = "home" | "map" | "simulation" | "impact" | "comparison";

type SphResponse = {
  status?: string;
  site?: string;
  model?: string;
  solver?: string;
  metadata?: any;
  products?: any;
  scientific_note?: string;
};

function apiUrl(path: string) {
  return `${API_BASE_URL}${path}`;
}

/*
 * IMPORTANT:
 * The current DualSPHysics pilot grid is local Cartesian data (x/y in metres),
 * not a georeferenced inundation raster. Therefore this screen uses the real
 * Mettur map as the geographic context and clearly labels the flow corridor
 * as a prototype visualization. It does NOT claim that the polygon is a
 * validated real-world inundation boundary.
 */

const riverPath = [
  { latitude: 11.8025, longitude: 77.7988 },
  { latitude: 11.7994, longitude: 77.8030 },
  { latitude: 11.7958, longitude: 77.8080 },
  { latitude: 11.7918, longitude: 77.8129 },
  { latitude: 11.7872, longitude: 77.8174 },
  { latitude: 11.7818, longitude: 77.8215 },
  { latitude: 11.7760, longitude: 77.8260 },
  { latitude: 11.7702, longitude: 77.8315 },
  { latitude: 11.7645, longitude: 77.8370 },
  { latitude: 11.7587, longitude: 77.8427 },
  { latitude: 11.7529, longitude: 77.8480 },
];

const floodCorridor = [
  { latitude: 11.8019, longitude: 77.7971 },
  { latitude: 11.7978, longitude: 77.8011 },
  { latitude: 11.7937, longitude: 77.8061 },
  { latitude: 11.7896, longitude: 77.8114 },
  { latitude: 11.7849, longitude: 77.8163 },
  { latitude: 11.7796, longitude: 77.8206 },
  { latitude: 11.7738, longitude: 77.8253 },
  { latitude: 11.7677, longitude: 77.8310 },
  { latitude: 11.7618, longitude: 77.8369 },
  { latitude: 11.7561, longitude: 77.8428 },
  { latitude: 11.7508, longitude: 77.8482 },
  { latitude: 11.7487, longitude: 77.8460 },
  { latitude: 11.7541, longitude: 77.8404 },
  { latitude: 11.7596, longitude: 77.8344 },
  { latitude: 11.7655, longitude: 77.8287 },
  { latitude: 11.7718, longitude: 77.8232 },
  { latitude: 11.7776, longitude: 77.8183 },
  { latitude: 11.7829, longitude: 77.8137 },
  { latitude: 11.7878, longitude: 77.8087 },
  { latitude: 11.7920, longitude: 77.8035 },
  { latitude: 11.7960, longitude: 77.7993 },
  { latitude: 11.8019, longitude: 77.7971 },
];

const impactZones = [
  [
    { latitude: 11.7984, longitude: 77.8004 },
    { latitude: 11.7955, longitude: 77.8040 },
    { latitude: 11.7932, longitude: 77.8018 },
    { latitude: 11.7960, longitude: 77.7988 },
  ],
  [
    { latitude: 11.7862, longitude: 77.8120 },
    { latitude: 11.7820, longitude: 77.8170 },
    { latitude: 11.7788, longitude: 77.8144 },
    { latitude: 11.7827, longitude: 77.8095 },
  ],
  [
    { latitude: 11.7722, longitude: 77.8258 },
    { latitude: 11.7681, longitude: 77.8314 },
    { latitude: 11.7639, longitude: 77.8280 },
    { latitude: 11.7681, longitude: 77.8222 },
  ],
];

function Header({ title, subtitle, onBack }: {
  title: string;
  subtitle?: string;
  onBack?: () => void;
}) {
  return (
    <View style={styles.header}>
      {onBack ? (
        <TouchableOpacity onPress={onBack} style={styles.backButton}>
          <Ionicons name="arrow-back" size={25} color={COLORS.greenDark} />
        </TouchableOpacity>
      ) : (
        <View style={styles.logoMark}>
          <Ionicons name="water-outline" size={26} color={COLORS.greenDark} />
        </View>
      )}

      <View style={{ flex: 1 }}>
        <Text style={styles.brand}>NEERAKSH</Text>
        <Text style={styles.brandSub}>Flood Intelligence</Text>
      </View>

      <View style={styles.statusPill}>
        <View style={styles.statusDot} />
        <Text style={styles.statusText}>SPH PILOT</Text>
      </View>
    </View>
  );
}

function SectionTitle({ title, action, onAction }: {
  title: string;
  action?: string;
  onAction?: () => void;
}) {
  return (
    <View style={styles.sectionRow}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {action && (
        <TouchableOpacity onPress={onAction}>
          <Text style={styles.sectionAction}>{action}</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

function MetricCard({
  icon,
  label,
  value,
  unit,
  accent = COLORS.green,
}: {
  icon: any;
  label: string;
  value: string;
  unit?: string;
  accent?: string;
}) {
  return (
    <View style={styles.metricCard}>
      <View style={[styles.metricIcon, { backgroundColor: `${accent}18` }]}>
        <Ionicons name={icon} size={21} color={accent} />
      </View>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={styles.metricValue}>{value}</Text>
      {unit ? <Text style={styles.metricUnit}>{unit}</Text> : null}
    </View>
  );
}

function BottomNav({
  active,
  onChange,
}: {
  active: ScreenName;
  onChange: (s: ScreenName) => void;
}) {
  const items: { key: ScreenName; icon: any; label: string }[] = [
    { key: "home", icon: "grid-outline", label: "Dashboard" },
    { key: "map", icon: "map-outline", label: "Flow Map" },
    { key: "simulation", icon: "pulse-outline", label: "Simulation" },
    { key: "impact", icon: "warning-outline", label: "Impact" },
  ];

  return (
    <View style={styles.bottomNav}>
      {items.map((item) => {
        const selected = active === item.key;
        return (
          <TouchableOpacity
            key={item.key}
            style={styles.navItem}
            onPress={() => onChange(item.key)}
          >
            <Ionicons
              name={item.icon}
              size={22}
              color={selected ? COLORS.greenDark : "#819088"}
            />
            <Text style={[styles.navLabel, selected && styles.navLabelActive]}>
              {item.label}
            </Text>
            {selected && <View style={styles.navIndicator} />}
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

function HomeScreen({
  sph,
  onMap,
  onSimulation,
}: {
  sph: SphResponse | null;
  onMap: () => void;
  onSimulation: () => void;
}) {
  const meta = sph?.metadata || {};

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="dark-content" backgroundColor={COLORS.white} />
      <Header />

      <ScrollView contentContainerStyle={styles.page}>
        <View style={styles.hero}>
          <View style={styles.heroTop}>
            <View style={{ flex: 1 }}>
              <Text style={styles.kicker}>DAM-BREAK INTELLIGENCE</Text>
              <Text style={styles.heroTitle}>Mettur Dam</Text>
              <Text style={styles.heroSub}>
                Real-time-ready prototype for breach-flow assessment
              </Text>
            </View>
            <View style={styles.indiaMark}>
              <Text style={styles.indiaMarkText}>IN</Text>
            </View>
          </View>

          <View style={styles.tricolor}>
            <View style={{ flex: 1, backgroundColor: COLORS.saffron }} />
            <View style={{ flex: 1, backgroundColor: COLORS.white }} />
            <View style={{ flex: 1, backgroundColor: COLORS.green }} />
          </View>

          <View style={styles.heroStats}>
            <View>
              <Text style={styles.heroStatLabel}>SCENARIO</Text>
              <Text style={styles.heroStatValue}>50 m breach</Text>
            </View>
            <View>
              <Text style={styles.heroStatLabel}>SOLVER</Text>
              <Text style={styles.heroStatValue}>DualSPHysics</Text>
            </View>
            <View>
              <Text style={styles.heroStatLabel}>RUN</Text>
              <Text style={styles.heroStatValue}>5.0 s</Text>
            </View>
          </View>
        </View>

        <SectionTitle title="Simulation indicators" />

        <View style={styles.metricGrid}>
          <MetricCard
            icon="layers-outline"
            label="MAX DEPTH"
            value={Number(meta.maximum_depth_m || 0).toFixed(1)}
            unit="m"
            accent={COLORS.water}
          />
          <MetricCard
            icon="speedometer-outline"
            label="MAX VELOCITY"
            value={Number(meta.maximum_velocity_mps || 0).toFixed(1)}
            unit="m/s"
            accent={COLORS.saffronDark}
          />
          <MetricCard
            icon="time-outline"
            label="ARRIVAL"
            value={Number(meta.earliest_downstream_arrival_s || 0).toFixed(1)}
            unit="s"
            accent={COLORS.green}
          />
          <MetricCard
            icon="navigate-outline"
            label="FLOW FRONT"
            value={Number(meta.fluid_front_final_x || 0).toFixed(0)}
            unit="local m"
            accent={COLORS.greenDark}
          />
        </View>

        <SectionTitle title="Flow model" />

        <TouchableOpacity style={styles.mapPreview} onPress={onMap} activeOpacity={0.9}>
          <MapView
            style={StyleSheet.absoluteFillObject}
            provider={Platform.OS === "android" ? PROVIDER_GOOGLE : undefined}
            initialRegion={{
              latitude: 11.803,
              longitude: 77.817,
              latitudeDelta: 0.08,
              longitudeDelta: 0.09,
            }}
            scrollEnabled={false}
            zoomEnabled={false}
            rotateEnabled={false}
            pitchEnabled={false}
          >
            <Polyline
              coordinates={riverPath}
              strokeColor={COLORS.water}
              strokeWidth={5}
            />
            <Polygon
              coordinates={floodCorridor}
              fillColor="rgba(19,138,75,0.20)"
              strokeColor="rgba(19,138,75,0.65)"
              strokeWidth={1.5}
            />
            <Marker coordinate={DAM}>
              <View style={styles.previewMarker}>
                <Ionicons name="water" size={16} color={COLORS.white} />
              </View>
            </Marker>
          </MapView>

          <View style={styles.mapPreviewOverlay}>
            <View>
              <Text style={styles.mapPreviewTitle}>Mettur downstream flow</Text>
              <Text style={styles.mapPreviewSub}>Tap to open live map</Text>
            </View>
            <View style={styles.openCircle}>
              <Ionicons name="arrow-forward" size={19} color={COLORS.greenDark} />
            </View>
          </View>
        </TouchableOpacity>

        <View style={styles.noteCard}>
          <Ionicons name="information-circle-outline" size={21} color={COLORS.saffronDark} />
          <Text style={styles.noteText}>
            Current SPH outputs are pilot particle-derived products. The geographic
            overlay is a prototype flow visualization, not a validated inundation forecast.
          </Text>
        </View>

        <TouchableOpacity style={styles.primaryButton} onPress={onSimulation}>
          <Ionicons name="play-circle-outline" size={23} color={COLORS.white} />
          <Text style={styles.primaryButtonText}>OPEN SIMULATION RESULTS</Text>
        </TouchableOpacity>
      </ScrollView>

      <BottomNav active="home" onChange={() => {}} />
    </SafeAreaView>
  );
}

function FlowMapScreen({ onBack }: { onBack: () => void }) {
  const [layer, setLayer] = useState<"depth" | "velocity" | "arrival">("depth");

  const title =
    layer === "depth"
      ? "Flood depth"
      : layer === "velocity"
      ? "Flow velocity"
      : "Arrival time";

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="dark-content" backgroundColor={COLORS.white} />
      <Header title="Flow Map" subtitle="Mettur" onBack={onBack} />

      <View style={styles.mapTitleBlock}>
        <View>
          <Text style={styles.mapTitle}>Mettur dam-break flow map</Text>
          <Text style={styles.mapSubtitle}>
            Real Mettur geographic map · 50 m breach pilot
          </Text>
        </View>
        <View style={styles.liveBadge}>
          <View style={styles.liveDot} />
          <Text style={styles.liveText}>PILOT</Text>
        </View>
      </View>

      <View style={styles.layerTabs}>
        {[
          ["depth", "Depth", "layers-outline"],
          ["velocity", "Velocity", "speedometer-outline"],
          ["arrival", "Arrival", "time-outline"],
        ].map(([key, label, icon]) => (
          <TouchableOpacity
            key={key}
            onPress={() => setLayer(key as any)}
            style={[styles.layerTab, layer === key && styles.layerTabActive]}
          >
            <Ionicons
              name={icon as any}
              size={17}
              color={layer === key ? COLORS.greenDark : COLORS.muted}
            />
            <Text style={[styles.layerTabText, layer === key && styles.layerTabTextActive]}>
              {label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <View style={styles.realMapContainer}>
        <MapView
          style={StyleSheet.absoluteFillObject}
          provider={Platform.OS === "android" ? PROVIDER_GOOGLE : undefined}
          mapType="standard"
          initialRegion={{
            latitude: 11.803,
            longitude: 77.817,
            latitudeDelta: 0.055,
            longitudeDelta: 0.065,
          }}
          showsCompass
          showsScale
          showsBuildings
          showsPointsOfInterest
          showsTraffic={false}
        >
          {/* Real geographic context */}
          <Marker coordinate={DAM}>
            <View style={styles.damMarker}>
              <Ionicons name="business" size={16} color={COLORS.white} />
              <Text style={styles.damMarkerText}>DAM</Text>
            </View>
          </Marker>

          {/* Real geographic map only. The actual river/roads/terrain come from the map provider. */}
          <Circle
            center={DAM}
            radius={250}
            fillColor="rgba(242,140,40,0.08)"
            strokeColor="rgba(242,140,40,0.45)"
            strokeWidth={2}
          />
        </MapView>

        <View style={styles.mapFloatingTop}>
          <View style={styles.mapLegendCard}>
            <Text style={styles.mapLegendTitle}>{title.toUpperCase()}</Text>
            <View style={styles.legendGradient}>
              <View style={[styles.legendBlock, { backgroundColor: "#D9EFE7" }]} />
              <View style={[styles.legendBlock, { backgroundColor: "#9ED3C0" }]} />
              <View style={[styles.legendBlock, { backgroundColor: "#4EAD83" }]} />
              <View style={[styles.legendBlock, { backgroundColor: "#138A4B" }]} />
            </View>
            <View style={styles.legendLabels}>
              <Text style={styles.legendLabel}>LOW</Text>
              <Text style={styles.legendLabel}>HIGH</Text>
            </View>
          </View>
        </View>

        <View style={styles.mapFloatingBottom}>
          <View style={styles.flowInfo}>
            <View style={styles.infoRow}>
              <View style={[styles.infoDot, { backgroundColor: COLORS.saffron }]} />
              <Text style={styles.infoText}>Dam / breach zone</Text>
            </View>
            <View style={styles.infoRow}>
              <View style={[styles.infoDot, { backgroundColor: COLORS.water }]} />
              <Text style={styles.infoText}>Cauvery / river context</Text>
            </View>
            <View style={styles.infoRow}>
              <View style={[styles.infoDot, { backgroundColor: COLORS.green }]} />
              <Text style={styles.infoText}>SPH overlay — next stage</Text>
            </View>
          </View>
        </View>
      </View>

      <View style={styles.mapBottomCard}>
        <View style={styles.mapBottomHeader}>
          <View>
            <Text style={styles.mapBottomTitle}>Mettur geographic context</Text>
            <Text style={styles.mapBottomSub}>Mettur Dam → Cauvery downstream corridor</Text>
          </View>
          <Ionicons name="navigate" size={25} color={COLORS.greenDark} />
        </View>

        <View style={styles.flowMetrics}>
          <View>
            <Text style={styles.smallLabel}>MAX VELOCITY</Text>
            <Text style={styles.smallValue}>44.67 m/s</Text>
          </View>
          <View>
            <Text style={styles.smallLabel}>MAX DEPTH</Text>
            <Text style={styles.smallValue}>65.31 m</Text>
          </View>
          <View>
            <Text style={styles.smallLabel}>FIRST ARRIVAL</Text>
            <Text style={styles.smallValue}>1.20 s</Text>
          </View>
        </View>

        <Text style={styles.mapDisclaimer}>
          Real Mettur map shown from the device map provider. SPH results remain local-grid
          pilot data until the simulation domain is georeferenced.
        </Text>
      </View>
    </SafeAreaView>
  );
}

function SimulationScreen({
  sph,
  onBack,
}: {
  sph: SphResponse | null;
  onBack: () => void;
}) {
  const meta = sph?.metadata || {};

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="dark-content" backgroundColor={COLORS.white} />
      <Header onBack={onBack} title="Simulation" subtitle="DualSPHysics" />

      <ScrollView contentContainerStyle={styles.page}>
        <View style={styles.simHero}>
          <View style={styles.simStatus}>
            <View style={styles.statusDotLarge} />
            <Text style={styles.simStatusText}>SIMULATION COMPLETE</Text>
          </View>
          <Text style={styles.simTitle}>50 m dam-break pilot</Text>
          <Text style={styles.simSub}>
            Mettur · DualSPHysics · 26 output frames · 5.0 s
          </Text>
        </View>

        <SectionTitle title="Hydrodynamic indicators" />
        <View style={styles.metricGrid}>
          <MetricCard
            icon="layers-outline"
            label="MAX DEPTH"
            value={Number(meta.maximum_depth_m || 0).toFixed(2)}
            unit="m"
            accent={COLORS.water}
          />
          <MetricCard
            icon="speedometer-outline"
            label="MAX VELOCITY"
            value={Number(meta.maximum_velocity_mps || 0).toFixed(2)}
            unit="m/s"
            accent={COLORS.saffronDark}
          />
          <MetricCard
            icon="time-outline"
            label="FIRST ARRIVAL"
            value={Number(meta.earliest_downstream_arrival_s || 0).toFixed(2)}
            unit="s"
            accent={COLORS.green}
          />
          <MetricCard
            icon="arrow-forward-circle-outline"
            label="FINAL FRONT"
            value={Number(meta.fluid_front_final_x || 0).toFixed(1)}
            unit="local m"
            accent={COLORS.greenDark}
          />
        </View>

        <View style={styles.dataCard}>
          <Text style={styles.dataCardTitle}>Run configuration</Text>
          {[
            ["Breach width", "50 m"],
            ["Simulation time", "5.0 s"],
            ["Output interval", "0.2 s"],
            ["Frames", "26"],
            ["Fluid particles / frame", "5,785"],
            ["Fluid particle type", "Type 3"],
          ].map(([a, b]) => (
            <View style={styles.dataRow} key={a}>
              <Text style={styles.dataKey}>{a}</Text>
              <Text style={styles.dataValue}>{b}</Text>
            </View>
          ))}
        </View>

        <View style={styles.scientificCard}>
          <Ionicons name="flask-outline" size={23} color={COLORS.saffronDark} />
          <View style={{ flex: 1 }}>
            <Text style={styles.scientificTitle}>Scientific status</Text>
            <Text style={styles.scientificText}>
              Particle-derived SPH pilot products. These values demonstrate breach-flow
              propagation and post-processing; they are not a validated Mettur inundation forecast.
            </Text>
          </View>
        </View>
      </ScrollView>

      <BottomNav active="simulation" onChange={() => {}} />
    </SafeAreaView>
  );
}

function ImpactScreen({ onBack }: { onBack: () => void }) {
  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="dark-content" backgroundColor={COLORS.white} />
      <Header onBack={onBack} title="Impact" subtitle="Scenario assessment" />

      <ScrollView contentContainerStyle={styles.page}>
        <View style={styles.impactHero}>
          <Text style={styles.kicker}>DOWNSTREAM ASSESSMENT</Text>
          <Text style={styles.impactTitle}>Potential flow corridor</Text>
          <Text style={styles.impactSub}>
            Use the map to inspect the prototype downstream pathway from the dam.
          </Text>
        </View>

        {[
          {
            icon: "water-outline",
            title: "Flood depth",
            text: "Depth indicators are derived from the SPH particle field in the current pilot domain.",
            color: COLORS.water,
          },
          {
            icon: "speedometer-outline",
            title: "Flow velocity",
            text: "Velocity indicators highlight the strongest simulated movement during the breach run.",
            color: COLORS.saffronDark,
          },
          {
            icon: "time-outline",
            title: "Arrival timing",
            text: "Arrival values indicate when the processed local grid first crosses the configured threshold.",
            color: COLORS.green,
          },
        ].map((item) => (
          <View style={styles.impactCard} key={item.title}>
            <View style={[styles.impactIcon, { backgroundColor: `${item.color}18` }]}>
              <Ionicons name={item.icon as any} size={25} color={item.color} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.impactCardTitle}>{item.title}</Text>
              <Text style={styles.impactCardText}>{item.text}</Text>
            </View>
          </View>
        ))}

        <View style={styles.tricolorCard}>
          <View style={styles.triStripeSaffron} />
          <View style={styles.triStripeWhite}>
            <Text style={styles.triTitle}>NEERAKSH</Text>
            <Text style={styles.triText}>Observe · Simulate · Assess</Text>
          </View>
          <View style={styles.triStripeGreen} />
        </View>
      </ScrollView>

      <BottomNav active="impact" onChange={() => {}} />
    </SafeAreaView>
  );
}

function App() {
  const [screen, setScreen] = useState<ScreenName>("home");
  const [sph, setSph] = useState<SphResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSPH();
  }, []);

  async function loadSPH() {
    try {
      setLoading(true);
      const response = await fetch(apiUrl("/api/simulation/sph/mettur"));
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const json = await response.json();
      setSph(json);
    } catch (error) {
      console.log("SPH API error:", error);
      setSph({
        metadata: {
          maximum_depth_m: 65.309567,
          maximum_velocity_mps: 44.668749,
          earliest_downstream_arrival_s: 1.2,
          fluid_front_final_x: 631.01855,
        },
      });
    } finally {
      setLoading(false);
    }
  }

  if (loading && screen === "home") {
    return (
      <SafeAreaView style={styles.loadingScreen}>
        <StatusBar barStyle="dark-content" backgroundColor={COLORS.white} />
        <View style={styles.loadingLogo}>
          <Ionicons name="water-outline" size={42} color={COLORS.greenDark} />
        </View>
        <Text style={styles.loadingBrand}>NEERAKSH</Text>
        <Text style={styles.loadingSub}>Loading flood intelligence</Text>
        <ActivityIndicator
          size="small"
          color={COLORS.greenDark}
          style={{ marginTop: 22 }}
        />
      </SafeAreaView>
    );
  }

  if (screen === "map") {
    return <FlowMapScreen onBack={() => setScreen("home")} />;
  }

  if (screen === "simulation") {
    return <SimulationScreen sph={sph} onBack={() => setScreen("home")} />;
  }

  if (screen === "impact") {
    return <ImpactScreen onBack={() => setScreen("home")} />;
  }

  return (
    <HomeScreen
      sph={sph}
      onMap={() => setScreen("map")}
      onSimulation={() => setScreen("simulation")}
    />
  );
}

const { width } = Dimensions.get("window");

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: COLORS.bg,
  },
  loadingScreen: {
    flex: 1,
    backgroundColor: COLORS.white,
    alignItems: "center",
    justifyContent: "center",
  },
  loadingLogo: {
    width: 74,
    height: 74,
    borderRadius: 37,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#EAF4EE",
    borderWidth: 2,
    borderColor: "#CDE3D5",
  },
  loadingBrand: {
    marginTop: 18,
    fontSize: 29,
    fontWeight: "900",
    letterSpacing: 5,
    color: COLORS.ink,
  },
  loadingSub: {
    marginTop: 5,
    fontSize: 14,
    color: COLORS.muted,
  },
  header: {
    minHeight: 76,
    backgroundColor: COLORS.white,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.line,
    paddingHorizontal: 18,
    flexDirection: "row",
    alignItems: "center",
  },
  logoMark: {
    width: 44,
    height: 44,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#EDF7F0",
    marginRight: 10,
  },
  backButton: {
    width: 42,
    height: 42,
    alignItems: "center",
    justifyContent: "center",
    marginRight: 4,
  },
  brand: {
    fontSize: 23,
    fontWeight: "900",
    letterSpacing: 4,
    color: COLORS.ink,
  },
  brandSub: {
    fontSize: 11,
    color: COLORS.muted,
    marginTop: 1,
    letterSpacing: 0.3,
  },
  statusPill: {
    borderWidth: 1,
    borderColor: "#B8D4C3",
    backgroundColor: "#F5FBF7",
    borderRadius: 17,
    paddingHorizontal: 10,
    height: 32,
    flexDirection: "row",
    alignItems: "center",
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: COLORS.green,
    marginRight: 6,
  },
  statusText: {
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 0.5,
    color: COLORS.greenDark,
  },
  page: {
    padding: 16,
    paddingBottom: 105,
  },
  hero: {
    backgroundColor: COLORS.white,
    borderRadius: 20,
    padding: 18,
    borderWidth: 1,
    borderColor: COLORS.line,
    overflow: "hidden",
    shadowColor: "#000",
    shadowOpacity: 0.05,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 3 },
    elevation: 2,
  },
  heroTop: {
    flexDirection: "row",
    alignItems: "center",
  },
  kicker: {
    color: COLORS.saffronDark,
    fontSize: 10,
    fontWeight: "900",
    letterSpacing: 1.1,
    marginBottom: 5,
  },
  heroTitle: {
    color: COLORS.ink,
    fontSize: 29,
    fontWeight: "900",
  },
  heroSub: {
    color: COLORS.muted,
    fontSize: 13,
    lineHeight: 19,
    marginTop: 5,
    maxWidth: width * 0.7,
  },
  indiaMark: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: "#F1F5F2",
    borderWidth: 1,
    borderColor: COLORS.line,
    alignItems: "center",
    justifyContent: "center",
  },
  indiaMarkText: {
    fontWeight: "900",
    color: COLORS.greenDark,
    letterSpacing: 1,
  },
  tricolor: {
    height: 5,
    flexDirection: "row",
    marginTop: 17,
    borderRadius: 4,
    overflow: "hidden",
  },
  heroStats: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingTop: 16,
  },
  heroStatLabel: {
    color: "#89958F",
    fontSize: 9,
    fontWeight: "800",
    letterSpacing: 0.8,
  },
  heroStatValue: {
    color: COLORS.ink,
    fontSize: 12,
    fontWeight: "800",
    marginTop: 4,
  },
  sectionRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: 21,
    marginBottom: 10,
  },
  sectionTitle: {
    fontSize: 17,
    fontWeight: "900",
    color: COLORS.ink,
  },
  sectionAction: {
    fontSize: 12,
    fontWeight: "800",
    color: COLORS.greenDark,
  },
  metricGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
  },
  metricCard: {
    width: "48.5%",
    backgroundColor: COLORS.white,
    borderRadius: 16,
    padding: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: COLORS.line,
  },
  metricIcon: {
    width: 36,
    height: 36,
    borderRadius: 11,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 11,
  },
  metricLabel: {
    fontSize: 9,
    fontWeight: "800",
    color: "#87938D",
    letterSpacing: 0.8,
  },
  metricValue: {
    fontSize: 22,
    fontWeight: "900",
    color: COLORS.ink,
    marginTop: 3,
  },
  metricUnit: {
    fontSize: 10,
    color: COLORS.muted,
    marginTop: 1,
  },
  mapPreview: {
    height: 230,
    borderRadius: 18,
    overflow: "hidden",
    backgroundColor: "#DDE8E5",
    borderWidth: 1,
    borderColor: COLORS.line,
  },
  mapPreviewOverlay: {
    position: "absolute",
    left: 12,
    right: 12,
    bottom: 12,
    backgroundColor: "rgba(255,255,255,0.96)",
    borderRadius: 14,
    padding: 13,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  mapPreviewTitle: {
    color: COLORS.ink,
    fontSize: 14,
    fontWeight: "900",
  },
  mapPreviewSub: {
    color: COLORS.muted,
    fontSize: 11,
    marginTop: 2,
  },
  openCircle: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: "#EAF4EE",
    alignItems: "center",
    justifyContent: "center",
  },
  previewMarker: {
    width: 34,
    height: 34,
    borderRadius: 17,
    backgroundColor: COLORS.saffronDark,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 2,
    borderColor: COLORS.white,
  },
  noteCard: {
    marginTop: 12,
    padding: 14,
    borderRadius: 15,
    borderWidth: 1,
    borderColor: "#E9D5A9",
    backgroundColor: "#FFF9EA",
    flexDirection: "row",
    gap: 10,
  },
  noteText: {
    flex: 1,
    color: "#725D2C",
    fontSize: 11,
    lineHeight: 17,
  },
  primaryButton: {
    height: 52,
    marginTop: 14,
    backgroundColor: COLORS.greenDark,
    borderRadius: 15,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: 9,
  },
  primaryButtonText: {
    color: COLORS.white,
    fontSize: 12,
    fontWeight: "900",
    letterSpacing: 0.4,
  },
  bottomNav: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    height: 76,
    backgroundColor: COLORS.white,
    borderTopWidth: 1,
    borderTopColor: COLORS.line,
    flexDirection: "row",
    justifyContent: "space-around",
    paddingTop: 8,
    paddingBottom: 7,
  },
  navItem: {
    width: "24%",
    alignItems: "center",
    justifyContent: "center",
    position: "relative",
  },
  navLabel: {
    fontSize: 9,
    color: "#819088",
    fontWeight: "700",
    marginTop: 4,
  },
  navLabelActive: {
    color: COLORS.greenDark,
  },
  navIndicator: {
    position: "absolute",
    bottom: -5,
    width: 25,
    height: 3,
    borderRadius: 2,
    backgroundColor: COLORS.saffron,
  },
  mapTitleBlock: {
    backgroundColor: COLORS.white,
    paddingHorizontal: 16,
    paddingTop: 14,
    paddingBottom: 12,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  mapTitle: {
    fontSize: 20,
    fontWeight: "900",
    color: COLORS.ink,
  },
  mapSubtitle: {
    color: COLORS.muted,
    fontSize: 11,
    marginTop: 4,
  },
  liveBadge: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#F5FBF7",
    borderWidth: 1,
    borderColor: "#C5DCCB",
    borderRadius: 13,
    paddingHorizontal: 9,
    height: 27,
  },
  liveDot: {
    width: 7,
    height: 7,
    borderRadius: 4,
    backgroundColor: COLORS.green,
    marginRight: 5,
  },
  liveText: {
    fontSize: 9,
    fontWeight: "900",
    color: COLORS.greenDark,
  },
  layerTabs: {
    backgroundColor: COLORS.white,
    flexDirection: "row",
    paddingHorizontal: 13,
    paddingBottom: 10,
    gap: 8,
  },
  layerTab: {
    flex: 1,
    height: 40,
    borderRadius: 11,
    borderWidth: 1,
    borderColor: COLORS.line,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: 6,
    backgroundColor: "#FAFCFB",
  },
  layerTabActive: {
    backgroundColor: "#EAF4EE",
    borderColor: "#9FC7AD",
  },
  layerTabText: {
    fontSize: 10,
    fontWeight: "800",
    color: COLORS.muted,
  },
  layerTabTextActive: {
    color: COLORS.greenDark,
  },
  realMapContainer: {
    flex: 1,
    minHeight: 460,
    margin: 10,
    borderRadius: 18,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: "#C9D8D0",
    backgroundColor: "#DCE9E5",
  },
  mapFloatingTop: {
    position: "absolute",
    top: 12,
    left: 12,
  },
  mapLegendCard: {
    width: 135,
    backgroundColor: "rgba(255,255,255,0.95)",
    borderRadius: 13,
    padding: 10,
    shadowColor: "#000",
    shadowOpacity: 0.12,
    shadowRadius: 5,
    shadowOffset: { width: 0, height: 2 },
    elevation: 3,
  },
  mapLegendTitle: {
    fontSize: 9,
    fontWeight: "900",
    color: COLORS.ink,
    marginBottom: 7,
  },
  legendGradient: {
    flexDirection: "row",
    height: 10,
    borderRadius: 4,
    overflow: "hidden",
  },
  legendBlock: {
    flex: 1,
  },
  legendLabels: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: 4,
  },
  legendLabel: {
    fontSize: 7,
    fontWeight: "800",
    color: COLORS.muted,
  },
  mapFloatingBottom: {
    position: "absolute",
    left: 12,
    bottom: 12,
  },
  flowInfo: {
    backgroundColor: "rgba(255,255,255,0.95)",
    borderRadius: 13,
    padding: 10,
  },
  infoRow: {
    flexDirection: "row",
    alignItems: "center",
    marginVertical: 3,
  },
  infoDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    marginRight: 7,
  },
  infoText: {
    fontSize: 9,
    fontWeight: "700",
    color: COLORS.ink,
  },
  damMarker: {
    backgroundColor: COLORS.saffronDark,
    borderRadius: 12,
    paddingHorizontal: 8,
    paddingVertical: 5,
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    borderWidth: 2,
    borderColor: COLORS.white,
  },
  damMarkerText: {
    color: COLORS.white,
    fontSize: 8,
    fontWeight: "900",
  },
  flowArrow: {
    width: 27,
    height: 27,
    borderRadius: 14,
    backgroundColor: "rgba(20,126,158,0.92)",
    borderWidth: 2,
    borderColor: COLORS.white,
    alignItems: "center",
    justifyContent: "center",
    transform: [{ rotate: "0deg" }],
  },
  mapBottomCard: {
    backgroundColor: COLORS.white,
    borderTopWidth: 1,
    borderTopColor: COLORS.line,
    padding: 14,
    paddingBottom: 17,
  },
  mapBottomHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  mapBottomTitle: {
    fontSize: 14,
    fontWeight: "900",
    color: COLORS.ink,
  },
  mapBottomSub: {
    fontSize: 10,
    color: COLORS.muted,
    marginTop: 3,
  },
  flowMetrics: {
    marginTop: 12,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: "#EEF2EF",
    flexDirection: "row",
    justifyContent: "space-between",
  },
  smallLabel: {
    fontSize: 7,
    fontWeight: "900",
    color: "#8A9690",
    letterSpacing: 0.4,
  },
  smallValue: {
    fontSize: 13,
    fontWeight: "900",
    color: COLORS.ink,
    marginTop: 3,
  },
  mapDisclaimer: {
    fontSize: 9,
    lineHeight: 13,
    color: "#7A6B4B",
    backgroundColor: "#FFF9EA",
    padding: 8,
    borderRadius: 9,
    marginTop: 10,
  },
  simHero: {
    backgroundColor: COLORS.greenDark,
    borderRadius: 18,
    padding: 18,
    overflow: "hidden",
  },
  simStatus: {
    flexDirection: "row",
    alignItems: "center",
  },
  statusDotLarge: {
    width: 9,
    height: 9,
    borderRadius: 5,
    backgroundColor: "#8BE0A8",
    marginRight: 7,
  },
  simStatusText: {
    color: "#C8F1D5",
    fontSize: 9,
    fontWeight: "900",
    letterSpacing: 1,
  },
  simTitle: {
    color: COLORS.white,
    fontSize: 25,
    fontWeight: "900",
    marginTop: 12,
  },
  simSub: {
    color: "#C7DCCF",
    fontSize: 11,
    marginTop: 5,
  },
  dataCard: {
    backgroundColor: COLORS.white,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: COLORS.line,
    padding: 15,
    marginTop: 5,
  },
  dataCardTitle: {
    color: COLORS.ink,
    fontSize: 15,
    fontWeight: "900",
    marginBottom: 8,
  },
  dataRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: "#EEF2EF",
  },
  dataKey: {
    color: COLORS.muted,
    fontSize: 11,
  },
  dataValue: {
    color: COLORS.ink,
    fontSize: 11,
    fontWeight: "800",
  },
  scientificCard: {
    backgroundColor: "#FFF9EA",
    borderWidth: 1,
    borderColor: "#E9D5A9",
    borderRadius: 16,
    padding: 14,
    marginTop: 12,
    flexDirection: "row",
    gap: 11,
  },
  scientificTitle: {
    color: "#735A28",
    fontSize: 13,
    fontWeight: "900",
  },
  scientificText: {
    color: "#78683F",
    fontSize: 10,
    lineHeight: 16,
    marginTop: 4,
  },
  impactHero: {
    backgroundColor: COLORS.white,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: COLORS.line,
    padding: 18,
    marginBottom: 12,
  },
  impactTitle: {
    color: COLORS.ink,
    fontSize: 25,
    fontWeight: "900",
  },
  impactSub: {
    color: COLORS.muted,
    fontSize: 12,
    lineHeight: 18,
    marginTop: 6,
  },
  impactCard: {
    backgroundColor: COLORS.white,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: COLORS.line,
    padding: 14,
    flexDirection: "row",
    gap: 12,
    marginBottom: 10,
  },
  impactIcon: {
    width: 48,
    height: 48,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
  },
  impactCardTitle: {
    color: COLORS.ink,
    fontSize: 14,
    fontWeight: "900",
  },
  impactCardText: {
    color: COLORS.muted,
    fontSize: 11,
    lineHeight: 17,
    marginTop: 4,
  },
  tricolorCard: {
    borderRadius: 18,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: COLORS.line,
    marginTop: 5,
  },
  triStripeSaffron: {
    height: 12,
    backgroundColor: COLORS.saffron,
  },
  triStripeWhite: {
    backgroundColor: COLORS.white,
    padding: 19,
    alignItems: "center",
  },
  triTitle: {
    color: COLORS.ink,
    fontSize: 22,
    fontWeight: "900",
    letterSpacing: 4,
  },
  triText: {
    color: COLORS.muted,
    fontSize: 11,
    marginTop: 5,
  },
  triStripeGreen: {
    height: 12,
    backgroundColor: COLORS.green,
  },
});

export default App;
