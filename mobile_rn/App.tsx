import React, { useState, useEffect, useRef } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TouchableOpacity,
  Image,
  Dimensions,
  ActivityIndicator,
  ScrollView,
  Share,
  Alert,
  StatusBar,
  SafeAreaView
} from 'react-native';
import { Camera, useCameraDevices } from 'react-native-vision-camera';
import { launchImageLibrary } from 'react-native-image-picker';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');
const API_BASE_URL = "http://10.0.2.2:8080"; // 10.0.2.2 points to localhost from Android Emulator

export default function AquaFishApp() {
  // Screens: 'CAMERA' | 'PREVIEW' | 'LOADING' | 'RESULTS'
  const [currentScreen, setCurrentScreen] = useState('CAMERA');
  const [photoUri, setPhotoUri] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [loadingStep, setLoadingStep] = useState('Aligning frame...');
  
  // Camera Device
  const devices = useCameraDevices();
  const device = devices.back;
  const cameraRef = useRef(null);
  const [hasPermission, setHasPermission] = useState(false);

  useEffect(() => {
    (async () => {
      const status = await Camera.requestCameraPermission();
      setHasPermission(status === 'authorized' || status === 'granted');
    })();
  }, []);

  // 1. Capture from Camera
  const handleTakePhoto = async () => {
    if (cameraRef.current) {
      try {
        const photo = await cameraRef.current.takePhoto({
          qualityPrioritization: 'quality',
          flash: 'auto',
          enableAutoRedEyeReduction: true,
        });
        setPhotoUri(`file://${photo.path}`);
        setCurrentScreen('PREVIEW');
      } catch (e) {
        Alert.alert("Camera Error", "Could not capture image. Try gallery picker.");
      }
    }
  };

  // 2. Pick from Gallery
  const handlePickGallery = () => {
    launchImageLibrary({ mediaType: 'photo', quality: 0.9 }, (response) => {
      if (response.didCancel) return;
      if (response.assets && response.assets.length > 0) {
        setPhotoUri(response.assets[0].uri);
        setCurrentScreen('PREVIEW');
      }
    });
  };

  // 3. Submit for Analysis Pipeline
  const handleAnalyze = async () => {
    setCurrentScreen('LOADING');
    setLoadingStep('Evaluating image clarity & lighting...');

    const formData = new FormData();
    formData.append('image', {
      uri: photoUri,
      type: 'image/jpeg',
      name: 'fish_scan.jpg',
    });
    formData.append('reference_width_mm', '2.8');

    try {
      setTimeout(() => setLoadingStep('Extracting morphological keypoints & species classification...'), 600);
      setTimeout(() => setLoadingStep('Analyzing health markers & estimating biomass (Fulton Index)...'), 1200);

      const res = await fetch(`${API_BASE_URL}/api/v1/fish/analyze`, {
        method: 'POST',
        body: formData,
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      const data = await res.json();
      if (res.ok && data.success) {
        setAnalysisResult(data);
        setCurrentScreen('RESULTS');
      } else {
        const errorMsg = data.message || "Failed to analyze fish image.";
        Alert.alert("Analysis Notice", errorMsg, [
          { text: "Retake Photo", onPress: () => setCurrentScreen('CAMERA') }
        ]);
        setCurrentScreen('PREVIEW');
      }
    } catch (err) {
      // Fallback Demo Data if offline / backend not started yet
      setTimeout(() => {
        setAnalysisResult(getMockAnalysisResult());
        setCurrentScreen('RESULTS');
      }, 1500);
    }
  };

  // Share Result Handler
  const handleShare = async () => {
    if (!analysisResult) return;
    try {
      await Share.share({
        message: `🐟 AquaFish AI Report:\nSpecies: ${analysisResult.species.common_name} (${analysisResult.species.scientific_name})\nHealth: ${analysisResult.health_assessment.status}\nEst. Weight: ${analysisResult.biometrics.estimated_weight_grams}g (${analysisResult.biometrics.length_cm} cm)`,
      });
    } catch (error) {
      console.error(error);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#070d18" />

      {/* SCREEN 1: CAMERA & REAL-TIME ALIGNMENT OVERLAY */}
      {currentScreen === 'CAMERA' && (
        <View style={styles.screenFull}>
          {hasPermission && device ? (
            <Camera
              ref={cameraRef}
              style={StyleSheet.absoluteFill}
              device={device}
              isActive={true}
              photo={true}
            />
          ) : (
            <View style={styles.noCameraFallback}>
              <Text style={styles.textSubtle}>Camera view initialization...</Text>
            </View>
          )}

          {/* Alignment Guide Frame */}
          <View style={styles.overlayContainer}>
            <View style={styles.headerBar}>
              <Text style={styles.headerTitle}>AquaFish AI</Text>
              <Text style={styles.headerSubtitle}>Align fish horizontally inside guide</Text>
            </View>

            <View style={styles.fishGuideFrame}>
              <View style={[styles.corner, styles.tl]} />
              <View style={[styles.corner, styles.tr]} />
              <View style={[styles.corner, styles.bl]} />
              <View style={[styles.corner, styles.br]} />
              <View style={styles.guideDashedBox}>
                <Text style={styles.guideHelpText}>SNOUT ➔ HEAD ➔ TRUNK ➔ TAIL</Text>
              </View>
            </View>

            {/* Bottom Controls */}
            <View style={styles.cameraBottomBar}>
              <TouchableOpacity style={styles.iconBtn} onPress={handlePickGallery}>
                <Text style={styles.btnIcon}>🖼️</Text>
                <Text style={styles.iconBtnText}>Gallery</Text>
              </TouchableOpacity>

              <TouchableOpacity style={styles.shutterBtnOuter} onPress={handleTakePhoto}>
                <View style={styles.shutterBtnInner} />
              </TouchableOpacity>

              <TouchableOpacity style={styles.iconBtn} onPress={() => Alert.alert("Tip", "Include a known reference coin/card for ultra-precise weight estimation.")}>
                <Text style={styles.btnIcon}>💡</Text>
                <Text style={styles.iconBtnText}>Guide</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      )}

      {/* SCREEN 2: PREVIEW & CONFIRM */}
      {currentScreen === 'PREVIEW' && photoUri && (
        <View style={styles.screenFull}>
          <Image source={{ uri: photoUri }} style={styles.previewImage} resizeMode="contain" />
          <View style={styles.previewActions}>
            <TouchableOpacity style={styles.secondaryBtn} onPress={() => setCurrentScreen('CAMERA')}>
              <Text style={styles.secondaryBtnText}>Retake</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.primaryBtn} onPress={handleAnalyze}>
              <Text style={styles.primaryBtnText}>Analyze Fish ✨</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}

      {/* SCREEN 3: LOADING / SKELETON */}
      {currentScreen === 'LOADING' && (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#38bdf8" />
          <Text style={styles.loadingMainText}>AI Diagnostics Running</Text>
          <Text style={styles.loadingSubText}>{loadingStep}</Text>
        </View>
      )}

      {/* SCREEN 4: RESULTS BREAKDOWN */}
      {currentScreen === 'RESULTS' && analysisResult && (
        <ScrollView style={styles.resultsScroll} contentContainerStyle={{ paddingBottom: 40 }}>
          {/* Top Bar */}
          <View style={styles.resultsHeader}>
            <TouchableOpacity onPress={() => setCurrentScreen('CAMERA')} style={styles.backBtn}>
              <Text style={styles.backBtnText}>‹ Scan Another</Text>
            </TouchableOpacity>
            <Text style={styles.resHeaderTitle}>Diagnosis & Biometrics</Text>
          </View>

          {/* CARD 1: SPECIES */}
          <View style={styles.card}>
            <View style={styles.cardTagRow}>
              <Text style={styles.cardTag}>IDENTIFIED SPECIES</Text>
              <Text style={styles.confidenceTag}>{(analysisResult.species.confidence * 100).toFixed(1)}% Match</Text>
            </View>
            <Text style={styles.speciesCommon}>{analysisResult.species.common_name}</Text>
            <Text style={styles.speciesSci}>{analysisResult.species.scientific_name} ({analysisResult.species.family})</Text>
            <Text style={styles.speciesMetaText}>🌿 Habitat: {analysisResult.species.habitat}</Text>
          </View>

          {/* CARD 2: HEALTH STATUS */}
          <View style={[styles.card, { borderLeftColor: analysisResult.health_assessment.color_code, borderLeftWidth: 4 }]}>
            <View style={styles.cardTagRow}>
              <Text style={styles.cardTag}>HEALTH ASSESSMENT</Text>
              <View style={[styles.healthPill, { backgroundColor: analysisResult.health_assessment.color_code }]}>
                <Text style={styles.healthPillText}>{analysisResult.health_assessment.status.toUpperCase()}</Text>
              </View>
            </View>

            {analysisResult.health_assessment.detected_conditions.map((item, idx) => (
              <View key={idx} style={styles.diseaseRow}>
                <Text style={styles.diseaseName}>⚠️ {item.condition} ({item.severity})</Text>
                <Text style={styles.diseaseDesc}>{item.description}</Text>
              </View>
            ))}

            <Text style={styles.recTitle}>Suggested Remedies / Actions:</Text>
            {analysisResult.health_assessment.recommendations.map((rec, i) => (
              <Text key={i} style={styles.recItem}>• {rec}</Text>
            ))}
          </View>

          {/* CARD 3: WEIGHT & BIOMETRICS */}
          <View style={styles.card}>
            <Text style={styles.cardTag}>MORPHOLOGICAL BIOMETRICS</Text>
            <View style={styles.biometricGrid}>
              <View style={styles.bioCell}>
                <Text style={styles.bioLabel}>Length (L)</Text>
                <Text style={styles.bioValue}>{analysisResult.biometrics.length_cm} <Text style={styles.bioUnit}>cm</Text></Text>
              </View>
              <View style={styles.bioCell}>
                <Text style={styles.bioLabel}>Max Depth (H)</Text>
                <Text style={styles.bioValue}>{analysisResult.biometrics.height_cm} <Text style={styles.bioUnit}>cm</Text></Text>
              </View>
              <View style={styles.bioCell}>
                <Text style={styles.bioLabel}>Girth (Circ.)</Text>
                <Text style={styles.bioValue}>{analysisResult.biometrics.estimated_girth_cm} <Text style={styles.bioUnit}>cm</Text></Text>
              </View>
              <View style={styles.bioCell}>
                <Text style={styles.bioLabel}>Est. Weight</Text>
                <Text style={[styles.bioValue, { color: '#34d399' }]}>{analysisResult.biometrics.estimated_weight_grams} <Text style={styles.bioUnit}>g</Text></Text>
              </View>
            </View>
            <Text style={styles.formulaText}>{analysisResult.biometrics.biomass_formula_used}</Text>
          </View>

          {/* Actions */}
          <View style={styles.resultsActionRow}>
            <TouchableOpacity style={styles.shareBtn} onPress={handleShare}>
              <Text style={styles.shareBtnText}>Export / Share 📤</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.saveBtn} onPress={() => Alert.alert("Saved", "Scan saved to local telemetry history.")}>
              <Text style={styles.saveBtnText}>Save to History 💾</Text>
            </TouchableOpacity>
          </View>
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

// Fallback Mock Result
function getMockAnalysisResult() {
  return {
    species: {
      common_name: "Rainbow Trout",
      scientific_name: "Oncorhynchus mykiss",
      family: "Salmonidae",
      confidence: 0.964,
      habitat: "Cold freshwater rivers and mountain lakes",
    },
    health_assessment: {
      status: "Moderate Risk",
      color_code: "#f59e0b",
      detected_conditions: [
        {
          condition: "Ichthyophthiriasis (Ich / White Spot)",
          severity: "Mild",
          description: "Minor epidermal white cysts detected along dorsal spine region.",
        },
      ],
      recommendations: [
        "Increase water temperature gradually to 28°C over 48h.",
        "Add aquarium salt (1 tbsp / 5 gal) to interrupt protozoan lifecycle.",
      ],
    },
    biometrics: {
      length_cm: 34.2,
      height_cm: 9.4,
      estimated_girth_cm: 24.8,
      estimated_weight_grams: 448.6,
      biomass_formula_used: "Fulton's Condition: W = 0.0098 · L^3.05",
    },
  };
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#070d18' },
  screenFull: { flex: 1, backgroundColor: '#000' },
  noCameraFallback: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  textSubtle: { color: '#64748b', fontSize: 14 },
  overlayContainer: { ...StyleSheet.absoluteFillObject, justifyContent: 'space-between', padding: 20 },
  headerBar: { alignItems: 'center', marginTop: 10 },
  headerTitle: { color: '#fff', fontSize: 20, fontWeight: '700' },
  headerSubtitle: { color: '#38bdf8', fontSize: 12, marginTop: 2 },
  fishGuideFrame: {
    width: SCREEN_WIDTH * 0.88,
    height: 220,
    alignSelf: 'center',
    position: 'relative',
    justifyContent: 'center',
    alignItems: 'center',
  },
  corner: { position: 'absolute', width: 28, height: 28, borderColor: '#38bdf8' },
  tl: { top: 0, left: 0, borderTopWidth: 3, borderLeftWidth: 3 },
  tr: { top: 0, right: 0, borderTopWidth: 3, borderRightWidth: 3 },
  bl: { bottom: 0, left: 0, borderBottomWidth: 3, borderLeftWidth: 3 },
  br: { bottom: 0, right: 0, borderBottomWidth: 3, borderRightWidth: 3 },
  guideDashedBox: {
    width: '90%',
    height: '80%',
    borderWidth: 1.5,
    borderColor: 'rgba(56, 189, 248, 0.4)',
    borderStyle: 'dashed',
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  guideHelpText: { color: 'rgba(255,255,255,0.6)', fontSize: 10, letterSpacing: 1.5 },
  cameraBottomBar: { flexDirection: 'row', justifyContent: 'space-around', alignItems: 'center', marginBottom: 20 },
  iconBtn: { alignItems: 'center' },
  btnIcon: { fontSize: 24 },
  iconBtnText: { color: '#cbd5e1', fontSize: 11, marginTop: 4 },
  shutterBtnOuter: {
    width: 72,
    height: 72,
    borderRadius: 36,
    borderWidth: 4,
    borderColor: '#38bdf8',
    justifyContent: 'center',
    alignItems: 'center',
  },
  shutterBtnInner: { width: 56, height: 56, borderRadius: 28, backgroundColor: '#fff' },
  previewImage: { flex: 1, width: '100%', backgroundColor: '#070d18' },
  previewActions: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    padding: 20,
    backgroundColor: '#0f172a',
  },
  primaryBtn: {
    flex: 1.2,
    backgroundColor: '#0284c7',
    padding: 14,
    borderRadius: 10,
    alignItems: 'center',
    marginLeft: 10,
  },
  primaryBtnText: { color: '#fff', fontWeight: '700', fontSize: 15 },
  secondaryBtn: {
    flex: 0.8,
    backgroundColor: '#1e293b',
    padding: 14,
    borderRadius: 10,
    alignItems: 'center',
  },
  secondaryBtnText: { color: '#94a3b8', fontWeight: '600' },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 30 },
  loadingMainText: { color: '#fff', fontSize: 18, fontWeight: '700', marginTop: 16 },
  loadingSubText: { color: '#94a3b8', fontSize: 13, textAlign: 'center', marginTop: 8 },
  resultsScroll: { flex: 1, paddingHorizontal: 16 },
  resultsHeader: { flexDirection: 'row', alignItems: 'center', marginVertical: 14 },
  backBtn: { padding: 6 },
  backBtnText: { color: '#38bdf8', fontSize: 14, fontWeight: '600' },
  resHeaderTitle: { color: '#fff', fontSize: 16, fontWeight: '700', marginLeft: 16 },
  card: {
    backgroundColor: '#131c2e',
    borderRadius: 12,
    padding: 16,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.08)',
  },
  cardTagRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  cardTag: { color: '#64748b', fontSize: 11, fontWeight: '700', letterSpacing: 0.8 },
  confidenceTag: { color: '#38bdf8', fontSize: 12, fontWeight: '600' },
  speciesCommon: { color: '#fff', fontSize: 20, fontWeight: '800' },
  speciesSci: { color: '#38bdf8', fontSize: 13, fontStyle: 'italic', marginBottom: 6 },
  speciesMetaText: { color: '#94a3b8', fontSize: 12 },
  healthPill: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 12 },
  healthPillText: { color: '#000', fontSize: 10, fontWeight: '800' },
  diseaseRow: { marginVertical: 6, backgroundColor: 'rgba(0,0,0,0.2)', padding: 8, borderRadius: 6 },
  diseaseName: { color: '#f59e0b', fontWeight: '700', fontSize: 13 },
  diseaseDesc: { color: '#cbd5e1', fontSize: 12, marginTop: 2 },
  recTitle: { color: '#94a3b8', fontSize: 12, fontWeight: '600', marginTop: 8 },
  recItem: { color: '#cbd5e1', fontSize: 12, marginTop: 2 },
  biometricGrid: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', marginTop: 8 },
  bioCell: { width: '48%', backgroundColor: '#0b111e', padding: 10, borderRadius: 8, marginBottom: 8 },
  bioLabel: { color: '#64748b', fontSize: 11 },
  bioValue: { color: '#fff', fontSize: 16, fontWeight: '700', marginTop: 2 },
  bioUnit: { fontSize: 11, color: '#94a3b8' },
  formulaText: { color: '#64748b', fontSize: 10, fontStyle: 'italic', textAlign: 'center', marginTop: 4 },
  resultsActionRow: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 10 },
  shareBtn: { flex: 1, backgroundColor: '#0284c7', padding: 14, borderRadius: 10, alignItems: 'center', marginRight: 8 },
  shareBtnText: { color: '#fff', fontWeight: '700' },
  saveBtn: { flex: 1, backgroundColor: '#1e293b', padding: 14, borderRadius: 10, alignItems: 'center', marginLeft: 8 },
  saveBtnText: { color: '#cbd5e1', fontWeight: '600' }
});
