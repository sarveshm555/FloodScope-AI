import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as THREE from 'three';
import { GlobeMarker, GlobeCameraPreset } from '../types';
import {
  RotateCcw,
  Play,
  Pause,
  Plus,
  Minus,
  Compass,
  MapPin,
  ExternalLink,
  Sparkles
} from 'lucide-react';

interface EarthGlobeProps {
  markers: GlobeMarker[];
  presets: GlobeCameraPreset[];
  selectedMarkerId: string | null;
  onSelectMarker: (marker: GlobeMarker) => void;
  onExploreAoi: (aoiId: string) => void;
}

// Convert geographic lat/lon (degrees) to 3D Cartesian coordinates on sphere of radius R
function latLonToVector3(lat: number, lon: number, radius: number): THREE.Vector3 {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lon + 180) * (Math.PI / 180);
  const x = -radius * Math.sin(phi) * Math.cos(theta);
  const y = radius * Math.cos(phi);
  const z = radius * Math.sin(phi) * Math.sin(theta);
  return new THREE.Vector3(x, y, z);
}

export const EarthGlobe: React.FC<EarthGlobeProps> = ({
  markers,
  presets,
  selectedMarkerId,
  onSelectMarker,
  onExploreAoi,
}) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const [webglSupported, setWebglSupported] = useState<boolean>(true);
  const [loading, setLoading] = useState<boolean>(true);
  const [loadingProgress, setLoadingProgress] = useState<number>(0);
  const [autoRotate, setAutoRotate] = useState<boolean>(true);
  const [hoveredMarker, setHoveredMarker] = useState<GlobeMarker | null>(null);

  // References to Three.js objects
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const earthMeshRef = useRef<THREE.Mesh | null>(null);
  const cloudsMeshRef = useRef<THREE.Mesh | null>(null);
  const markersGroupRef = useRef<THREE.Group | null>(null);
  const markerHitboxesRef = useRef<{ mesh: THREE.Mesh; marker: GlobeMarker }[]>([]);
  const animFrameRef = useRef<number | null>(null);

  // Interaction & camera state
  const isDraggingRef = useRef<boolean>(false);
  const previousPointerPosRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const velocityRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const autoRotateRef = useRef<boolean>(true);
  const lastInteractionTimeRef = useRef<number>(Date.now());

  // Camera spherical coordinates: distance, lat, lon
  const cameraStateRef = useRef({
    distance: 3.2,
    targetDistance: 3.2,
    lat: 25.0,
    lon: 75.0,
    targetLat: 25.0,
    targetLon: 75.0,
    isAnimatingToTarget: false,
    animProgress: 1.0,
    animStart: { lat: 25.0, lon: 75.0, distance: 3.2 },
  });

  autoRotateRef.current = autoRotate;

  // Fly camera to a specific lat/lon and distance
  const flyTo = useCallback((lat: number, lon: number, distance: number = 2.0) => {
    const cs = cameraStateRef.current;
    cs.animStart = { lat: cs.lat, lon: cs.lon, distance: cs.distance };
    cs.targetLat = lat;
    cs.targetLon = lon;
    cs.targetDistance = distance;
    cs.animProgress = 0;
    cs.isAnimatingToTarget = true;
    lastInteractionTimeRef.current = Date.now();
  }, []);

  // Zoom helpers
  const handleZoomIn = () => {
    const cs = cameraStateRef.current;
    cs.targetDistance = Math.max(1.3, cs.targetDistance - 0.4);
    cs.isAnimatingToTarget = true;
  };

  const handleZoomOut = () => {
    const cs = cameraStateRef.current;
    cs.targetDistance = Math.min(5.0, cs.targetDistance + 0.4);
    cs.isAnimatingToTarget = true;
  };

  const handleResetCamera = () => {
    flyTo(presets[0]?.lat ?? 20, presets[0]?.lon ?? 45, presets[0]?.distance ?? 3.8);
  };

  // Check WebGL availability
  useEffect(() => {
    try {
      const canvas = document.createElement('canvas');
      const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
      if (!gl) {
        setWebglSupported(false);
      }
    } catch {
      setWebglSupported(false);
    }
  }, []);

  // Initialize Three.js scene
  useEffect(() => {
    if (!webglSupported || !mountRef.current) return;

    const container = mountRef.current;
    const width = container.clientWidth || window.innerWidth;
    const height = container.clientHeight || window.innerHeight;

    // 1. Scene
    const scene = new THREE.Scene();
    sceneRef.current = scene;
    scene.background = new THREE.Color('#030712'); // Deep space dark navy

    // 2. Camera
    const camera = new THREE.PerspectiveCamera(42, width / height, 0.1, 1000);
    cameraRef.current = camera;
    camera.position.set(0, 0, 3.2);

    // 3. Renderer
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance',
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // 4. Starfield background particles
    const starCount = 1200;
    const starPositions = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount; i++) {
      const r = 40 + Math.random() * 40;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      starPositions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      starPositions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      starPositions[i * 3 + 2] = r * Math.cos(phi);
    }
    const starGeom = new THREE.BufferGeometry();
    starGeom.setAttribute('position', new THREE.BufferAttribute(starPositions, 3));
    const starMat = new THREE.PointsMaterial({
      color: 0x94a3b8,
      size: 0.7,
      transparent: true,
      opacity: 0.65,
    });
    const starField = new THREE.Points(starGeom, starMat);
    scene.add(starField);

    // 5. Lighting
    const ambientLight = new THREE.AmbientLight(0x384252, 1.4); // Subtle celestial fill
    scene.add(ambientLight);

    const sunLight = new THREE.DirectionalLight(0xffffff, 2.4);
    sunLight.position.set(5, 3, 5);
    scene.add(sunLight);

    // Secondary rim light for cinematic atmospheric limb
    const rimLight = new THREE.DirectionalLight(0x38bdf8, 1.2);
    rimLight.position.set(-5, -2, -4);
    scene.add(rimLight);

    // 6. Texture Loading Manager
    const manager = new THREE.LoadingManager(
      () => {
        setLoading(false);
      },
      (_item, loaded, total) => {
        setLoadingProgress(Math.round((loaded / total) * 100));
      },
      (url) => {
        console.warn(`Texture failed to load from ${url}, falling back.`);
        setLoading(false);
      }
    );

    const textureLoader = new THREE.TextureLoader(manager);

    // Load Earth textures from local public textures directory
    const earthDayMap = textureLoader.load('/textures/earth_blue_marble.jpg');
    const earthNormalMap = textureLoader.load('/textures/earth_normal.jpg');
    const earthSpecularMap = textureLoader.load('/textures/earth_specular.jpg');
    const earthCloudsMap = textureLoader.load('/textures/earth_clouds.png');

    earthDayMap.colorSpace = THREE.SRGBColorSpace;
    earthCloudsMap.colorSpace = THREE.SRGBColorSpace;

    // 7. Earth Sphere Mesh
    const earthGeom = new THREE.SphereGeometry(1, 64, 64);
    const earthMat = new THREE.MeshPhongMaterial({
      map: earthDayMap,
      normalMap: earthNormalMap,
      normalScale: new THREE.Vector2(0.4, 0.4),
      specularMap: earthSpecularMap,
      specular: new THREE.Color(0x38bdf8),
      shininess: 22,
    });
    const earthMesh = new THREE.Mesh(earthGeom, earthMat);
    scene.add(earthMesh);
    earthMeshRef.current = earthMesh;

    // 8. Dynamic Translucent Clouds Layer
    const cloudsGeom = new THREE.SphereGeometry(1.012, 64, 64);
    const cloudsMat = new THREE.MeshStandardMaterial({
      map: earthCloudsMap,
      transparent: true,
      opacity: 0.65,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    const cloudsMesh = new THREE.Mesh(cloudsGeom, cloudsMat);
    scene.add(cloudsMesh);
    cloudsMeshRef.current = cloudsMesh;

    // 9. Atmospheric Fresnel Glow (Custom Shader)
    const atmosphereGeom = new THREE.SphereGeometry(1.18, 64, 64);
    const atmosphereMat = new THREE.ShaderMaterial({
      vertexShader: `
        varying vec3 vNormal;
        void main() {
          vNormal = normalize(normalMatrix * normal);
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        varying vec3 vNormal;
        void main() {
          float intensity = pow(0.68 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 2.8);
          gl_FragColor = vec4(0.07, 0.64, 0.98, 1.0) * intensity;
        }
      `,
      blending: THREE.AdditiveBlending,
      side: THREE.BackSide,
      transparent: true,
      depthWrite: false,
    });
    const atmosphereMesh = new THREE.Mesh(atmosphereGeom, atmosphereMat);
    scene.add(atmosphereMesh);

    // 10. Location Markers Group
    const markersGroup = new THREE.Group();
    scene.add(markersGroup);
    markersGroupRef.current = markersGroup;

    // 11. Populate 3D Markers
    const hitboxes: { mesh: THREE.Mesh; marker: GlobeMarker }[] = [];
    markers.forEach((m) => {
      const isPrimary = m.status === 'primary_active';
      const pos = latLonToVector3(m.lat, m.lon, 1.0);
      const normal = pos.clone().normalize();

      const markerObj = new THREE.Group();
      markerObj.position.copy(pos);

      // A. Ground Anchor Base (Pulsing ring)
      const ringGeom = new THREE.RingGeometry(0.015, 0.035, 32);
      const ringMat = new THREE.MeshBasicMaterial({
        color: isPrimary ? 0x00f0ff : 0x38bdf8,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.85,
      });
      const ringMesh = new THREE.Mesh(ringGeom, ringMat);
      ringMesh.lookAt(normal.clone().multiplyScalar(2));
      markerObj.add(ringMesh);

      // B. Vertical Beacon Spike (Line connecting surface to elevated point)
      const elevatedPos = normal.clone().multiplyScalar(0.065);
      const spikeGeom = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(0, 0, 0),
        elevatedPos,
      ]);
      const spikeMat = new THREE.LineBasicMaterial({
        color: isPrimary ? 0x38bdf8 : 0x0284c7,
        transparent: true,
        opacity: 0.75,
        linewidth: 2,
      });
      const spikeLine = new THREE.Line(spikeGeom, spikeMat);
      markerObj.add(spikeLine);

      // C. Elevated Glowing Core Sphere
      const sphereGeom = new THREE.SphereGeometry(0.018, 16, 16);
      const sphereMat = new THREE.MeshBasicMaterial({
        color: isPrimary ? 0x00f5ff : 0x38bdf8,
      });
      const sphereMesh = new THREE.Mesh(sphereGeom, sphereMat);
      sphereMesh.position.copy(elevatedPos);
      markerObj.add(sphereMesh);

      // D. Outer Aura Halo
      const haloGeom = new THREE.SphereGeometry(0.032, 16, 16);
      const haloMat = new THREE.MeshBasicMaterial({
        color: isPrimary ? 0x38bdf8 : 0x0284c7,
        transparent: true,
        opacity: 0.35,
        blending: THREE.AdditiveBlending,
      });
      const haloMesh = new THREE.Mesh(haloGeom, haloMat);
      haloMesh.position.copy(elevatedPos);
      markerObj.add(haloMesh);

      // E. Invisible Hitbox for Raycasting
      const hitboxGeom = new THREE.SphereGeometry(0.08, 8, 8);
      const hitboxMat = new THREE.MeshBasicMaterial({
        visible: false,
      });
      const hitboxMesh = new THREE.Mesh(hitboxGeom, hitboxMat);
      hitboxMesh.position.copy(elevatedPos);
      markerObj.add(hitboxMesh);
      hitboxes.push({ mesh: hitboxMesh, marker: m });

      markersGroup.add(markerObj);
    });
    markerHitboxesRef.current = hitboxes;

    // Handle Window Resize
    const handleResize = () => {
      if (!container || !renderer || !camera) return;
      const w = container.clientWidth || window.innerWidth;
      const h = container.clientHeight || window.innerHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    // Initial camera position aligned towards Trishuli / South Asia
    flyTo(27.98, 85.18, 2.4);

    // 12. Main Animation & Render Loop
    let lastTime = performance.now();
    const animate = (currentTime: number) => {
      animFrameRef.current = requestAnimationFrame(animate);

      const delta = Math.min((currentTime - lastTime) / 1000, 0.1);
      lastTime = currentTime;

      const cs = cameraStateRef.current;

      // Handle Smooth Camera Interpolation (flyTo)
      if (cs.isAnimatingToTarget) {
        cs.animProgress += delta * 1.5;
        if (cs.animProgress >= 1.0) {
          cs.animProgress = 1.0;
          cs.isAnimatingToTarget = false;
          cs.lat = cs.targetLat;
          cs.lon = cs.targetLon;
          cs.distance = cs.targetDistance;
        } else {
          // Smooth ease-out cubic
          const t = 1 - Math.pow(1 - cs.animProgress, 3);
          cs.lat = cs.animStart.lat + (cs.targetLat - cs.animStart.lat) * t;
          cs.lon = cs.animStart.lon + (cs.targetLon - cs.animStart.lon) * t;
          cs.distance = cs.animStart.distance + (cs.targetDistance - cs.animStart.distance) * t;
        }
      } else {
        // Continuous auto-rotation when enabled and user is idle
        const isIdle = Date.now() - lastInteractionTimeRef.current > 2500;
        if (autoRotateRef.current && isIdle && !isDraggingRef.current) {
          cs.lon -= 0.08 * (delta * 60);
          while (cs.lon < -180) cs.lon += 360;
        }

        // Apply drag damping velocity
        if (!isDraggingRef.current) {
          cs.lon += velocityRef.current.x;
          cs.lat = Math.max(-85, Math.min(85, cs.lat + velocityRef.current.y));
          velocityRef.current.x *= 0.92;
          velocityRef.current.y *= 0.92;
        }
      }

      // Update camera position from spherical lat/lon
      const camPos = latLonToVector3(cs.lat, cs.lon, cs.distance);
      camera.position.copy(camPos);
      camera.lookAt(0, 0, 0);

      // Subtle dynamic cloud layer rotation (faster than surface)
      if (cloudsMesh) {
        cloudsMesh.rotation.y += 0.0003;
      }

      // Animate pulsing rings on markers
      if (markersGroup) {
        const pulse = 1 + 0.18 * Math.sin(currentTime * 0.0035);
        markersGroup.children.forEach((group) => {
          const ring = group.children[0];
          if (ring) {
            ring.scale.set(pulse, pulse, pulse);
          }
        });
      }

      renderer.render(scene, camera);
    };

    animFrameRef.current = requestAnimationFrame(animate);

    // Cleanup resources on unmount
    return () => {
      window.removeEventListener('resize', handleResize);
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);

      // Dispose Three.js objects
      starGeom.dispose();
      starMat.dispose();
      earthGeom.dispose();
      earthMat.dispose();
      cloudsGeom.dispose();
      cloudsMat.dispose();
      atmosphereGeom.dispose();
      atmosphereMat.dispose();

      earthDayMap.dispose();
      earthNormalMap.dispose();
      earthSpecularMap.dispose();
      earthCloudsMap.dispose();

      renderer.dispose();
      renderer.forceContextLoss();

      if (container && renderer.domElement && container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, [webglSupported, markers, presets, flyTo]);

  // Handle Raycasting for Marker Selection & Hover
  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!rendererRef.current || !cameraRef.current) return;
    const rect = rendererRef.current.domElement.getBoundingClientRect();
    const mouse = new THREE.Vector2(
      ((e.clientX - rect.left) / rect.width) * 2 - 1,
      -((e.clientY - rect.top) / rect.height) * 2 + 1
    );

    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(mouse, cameraRef.current);

    const hitMeshes = markerHitboxesRef.current.map((h) => h.mesh);
    const intersects = raycaster.intersectObjects(hitMeshes, true);

    if (intersects.length > 0) {
      const hit = markerHitboxesRef.current.find((h) => h.mesh === intersects[0].object);
      if (hit) {
        setHoveredMarker(hit.marker);
        if (mountRef.current) mountRef.current.style.cursor = 'pointer';
        return;
      }
    }

    setHoveredMarker(null);
    if (mountRef.current) {
      mountRef.current.style.cursor = isDraggingRef.current ? 'grabbing' : 'grab';
    }
  };

  // Pointer Down (Start Drag)
  const handlePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    isDraggingRef.current = true;
    previousPointerPosRef.current = { x: e.clientX, y: e.clientY };
    velocityRef.current = { x: 0, y: 0 };
    lastInteractionTimeRef.current = Date.now();
    cameraStateRef.current.isAnimatingToTarget = false;
    if (mountRef.current) mountRef.current.style.cursor = 'grabbing';
  };

  // Pointer Move (Dragging)
  const handlePointerDrag = (e: React.PointerEvent<HTMLDivElement>) => {
    handlePointerMove(e);
    if (!isDraggingRef.current) return;

    const deltaX = e.clientX - previousPointerPosRef.current.x;
    const deltaY = e.clientY - previousPointerPosRef.current.y;
    previousPointerPosRef.current = { x: e.clientX, y: e.clientY };

    const sensitivity = 0.28;
    const cs = cameraStateRef.current;

    // Invert X rotation for natural spherical grab
    const dLon = -deltaX * sensitivity;
    const dLat = deltaY * sensitivity;

    cs.lon += dLon;
    cs.lat = Math.max(-85, Math.min(85, cs.lat + dLat));
    velocityRef.current = { x: dLon * 0.4, y: dLat * 0.4 };
    lastInteractionTimeRef.current = Date.now();
  };

  // Pointer Up (End Drag & Click check)
  const handlePointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    isDraggingRef.current = false;
    lastInteractionTimeRef.current = Date.now();
    if (mountRef.current) mountRef.current.style.cursor = 'grab';

    // Check if click hit a marker
    if (!rendererRef.current || !cameraRef.current) return;
    const rect = rendererRef.current.domElement.getBoundingClientRect();
    const mouse = new THREE.Vector2(
      ((e.clientX - rect.left) / rect.width) * 2 - 1,
      -((e.clientY - rect.top) / rect.height) * 2 + 1
    );

    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(mouse, cameraRef.current);
    const hitMeshes = markerHitboxesRef.current.map((h) => h.mesh);
    const intersects = raycaster.intersectObjects(hitMeshes, true);

    if (intersects.length > 0) {
      const hit = markerHitboxesRef.current.find((h) => h.mesh === intersects[0].object);
      if (hit) {
        onSelectMarker(hit.marker);
        flyTo(hit.marker.lat, hit.marker.lon, hit.marker.status === 'primary_active' ? 1.45 : 1.9);
      }
    }
  };

  // Wheel Zoom
  const handleWheel = (e: React.WheelEvent<HTMLDivElement>) => {
    e.preventDefault();
    const cs = cameraStateRef.current;
    const zoomDelta = e.deltaY * 0.002;
    cs.distance = Math.max(1.3, Math.min(5.0, cs.distance + zoomDelta));
    cs.targetDistance = cs.distance;
    cs.isAnimatingToTarget = false;
    lastInteractionTimeRef.current = Date.now();
  };

  // Keyboard accessibility
  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    const cs = cameraStateRef.current;
    if (e.key === 'ArrowLeft') {
      cs.lon -= 3;
      cs.isAnimatingToTarget = false;
    } else if (e.key === 'ArrowRight') {
      cs.lon += 3;
      cs.isAnimatingToTarget = false;
    } else if (e.key === 'ArrowUp') {
      cs.lat = Math.min(85, cs.lat + 3);
      cs.isAnimatingToTarget = false;
    } else if (e.key === 'ArrowDown') {
      cs.lat = Math.max(-85, cs.lat - 3);
      cs.isAnimatingToTarget = false;
    } else if (e.key === '+' || e.key === '=') {
      handleZoomIn();
    } else if (e.key === '-' || e.key === '_') {
      handleZoomOut();
    } else if (e.key === ' ') {
      e.preventDefault();
      setAutoRotate((prev) => !prev);
    }
  };

  const selectedMarker = markers.find((m) => m.id === selectedMarkerId) || markers[0];

  return (
    <div
      tabIndex={0}
      onKeyDown={handleKeyDown}
      className="relative w-full h-full min-h-[640px] bg-slate-950 overflow-hidden select-none outline-none focus-visible:ring-1 focus-visible:ring-sky-500"
    >
      {/* 2D Fallback when WebGL is unsupported */}
      {!webglSupported && (
        <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center z-20 bg-slate-950">
          <div className="p-4 bg-sky-950/80 rounded-2xl border border-sky-800/80 max-w-lg space-y-4 shadow-2xl">
            <Compass className="w-12 h-12 text-sky-400 mx-auto animate-spin" />
            <h3 className="text-lg font-bold text-slate-100">2D Cartographic Navigation Fallback</h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              Hardware WebGL 3D acceleration is currently disabled or unavailable on this system.
              FloodScope AI is running in high-contrast geographic fallback mode.
            </p>
            <div className="space-y-2 pt-2">
              {markers.map((m) => (
                <button
                  key={m.id}
                  onClick={() => {
                    onSelectMarker(m);
                    if (m.aoiId) onExploreAoi(m.aoiId);
                  }}
                  className="w-full py-2.5 px-4 rounded-lg bg-slate-900 border border-slate-700 hover:border-sky-500 text-xs text-left flex items-center justify-between"
                >
                  <span className="font-semibold text-slate-200">{m.name}</span>
                  <span className="text-sky-400 font-mono text-[11px]">{m.lat}° N, {m.lon}° E</span>
                </button>
              ))}
            </div>
            <button
              onClick={() => onExploreAoi('trishuli_nepal')}
              className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-sky-600 to-indigo-600 font-bold text-xs text-white shadow-lg"
            >
              Open Trishuli Flood Analysis Dashboard →
            </button>
          </div>
        </div>
      )}

      {/* Loading Overlay */}
      {loading && webglSupported && (
        <div className="absolute inset-0 flex flex-col items-center justify-center z-20 bg-slate-950/80 backdrop-blur-sm pointer-events-none transition-opacity duration-500">
          <div className="flex flex-col items-center space-y-3">
            <div className="w-10 h-10 border-2 border-sky-500/30 border-t-sky-400 rounded-full animate-spin" />
            <div className="text-xs font-semibold text-slate-200 tracking-wider uppercase">
              Initializing 3D Satellite Earth ({loadingProgress}%)
            </div>
            <span className="text-[10px] text-slate-400">Loading NASA Blue Marble surface textures...</span>
          </div>
        </div>
      )}

      {/* WebGL Mount Container */}
      <div
        ref={mountRef}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerDrag}
        onPointerUp={handlePointerUp}
        onWheel={handleWheel}
        className="w-full h-full cursor-grab active:cursor-grabbing"
        style={{ touchAction: 'none' }}
      />

      {/* Floating Header HUD / Presets */}
      <div className="absolute top-4 left-4 z-10 flex flex-wrap items-center gap-2">
        <div className="bg-slate-900/90 backdrop-blur-md px-3.5 py-1.5 rounded-xl border border-slate-700/80 shadow-2xl flex items-center space-x-2 text-xs">
          <Sparkles className="w-3.5 h-3.5 text-sky-400" />
          <span className="font-semibold text-slate-200">Orbital Earth View</span>
          <span className="text-[10px] px-1.5 py-0.2 rounded bg-sky-950 text-sky-300 border border-sky-800">
            Interactive 3D
          </span>
        </div>

        {/* Quick Camera Preset Buttons */}
        <div className="bg-slate-900/90 backdrop-blur-md p-1 rounded-xl border border-slate-700/80 shadow-2xl flex items-center space-x-1">
          {presets.map((p) => (
            <button
              key={p.id}
              onClick={() => flyTo(p.lat, p.lon, p.distance)}
              aria-label={`Fly camera to ${p.label}`}
              className="px-2.5 py-1 rounded-lg text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800/80 transition"
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Floating Globe Navigation Controls (Right Edge) */}
      <div className="absolute top-4 right-4 z-10 flex flex-col space-y-2">
        <div className="bg-slate-900/90 backdrop-blur-md p-1.5 rounded-xl border border-slate-700/80 shadow-2xl flex flex-col space-y-1.5">
          <button
            onClick={handleZoomIn}
            aria-label="Zoom in on Earth globe"
            title="Zoom In (+)"
            className="p-2 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800 transition"
          >
            <Plus className="w-4 h-4" />
          </button>
          <button
            onClick={handleZoomOut}
            aria-label="Zoom out of Earth globe"
            title="Zoom Out (-)"
            className="p-2 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800 transition"
          >
            <Minus className="w-4 h-4" />
          </button>
          <div className="w-full h-px bg-slate-800" />
          <button
            onClick={() => setAutoRotate((prev) => !prev)}
            aria-label={autoRotate ? 'Pause Earth rotation' : 'Resume Earth rotation'}
            title={autoRotate ? 'Pause Auto-Rotation' : 'Resume Auto-Rotation'}
            className={`p-2 rounded-lg transition ${
              autoRotate ? 'text-sky-400 bg-sky-950/60' : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            {autoRotate ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
          </button>
          <button
            onClick={handleResetCamera}
            aria-label="Reset Earth camera view"
            title="Reset Global View"
            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Hover Marker Tooltip */}
      {hoveredMarker && (
        <div className="absolute top-16 left-1/2 -translate-x-1/2 z-20 pointer-events-none bg-slate-900/95 backdrop-blur-md px-3 py-1.5 rounded-lg border border-sky-500/50 shadow-2xl text-xs flex items-center space-x-2 animate-fade-in">
          <MapPin className="w-3.5 h-3.5 text-sky-400" />
          <span className="font-semibold text-slate-100">{hoveredMarker.name}</span>
          <span className="text-slate-400">({hoveredMarker.country})</span>
        </div>
      )}

      {/* Selected Location Card & Action Drawer (Bottom Left) */}
      <div className="absolute bottom-6 left-6 z-10 max-w-sm w-full bg-slate-900/95 backdrop-blur-md p-4 rounded-2xl border border-slate-700/80 shadow-2xl space-y-3.5">
        <div className="flex items-start justify-between gap-2 border-b border-slate-800 pb-3">
          <div>
            <div className="flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-sky-400 animate-pulse" />
              <h3 className="font-bold text-slate-100 text-sm">{selectedMarker.name}</h3>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">{selectedMarker.region}, {selectedMarker.country}</p>
          </div>
          {selectedMarker.status === 'primary_active' ? (
            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800 whitespace-nowrap">
              Active Case Study
            </span>
          ) : (
            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-950/70 text-amber-300 border border-amber-800 whitespace-nowrap">
              Illustrative Candidate
            </span>
          )}
        </div>

        {/* Geographic Coordinates & Description */}
        <div className="space-y-2 text-xs">
          <div className="flex items-center justify-between p-2 rounded-lg bg-slate-950/70 border border-slate-800 font-mono text-[11px]">
            <span className="text-slate-400">Coordinates:</span>
            <span className="text-sky-300 font-semibold">{selectedMarker.lat.toFixed(3)}° N, {selectedMarker.lon.toFixed(3)}° E</span>
          </div>
          <p className="text-slate-300 text-[11px] leading-relaxed">
            {selectedMarker.description}
          </p>
        </div>

        {/* Data Status Summary */}
        <div className="space-y-1.5 pt-1 border-t border-slate-800 text-[11px]">
          <div className="flex items-center justify-between text-slate-300">
            <span className="text-slate-400">Copernicus DEM:</span>
            <span className="font-medium text-emerald-400">Verified GLO-30 Mosaic</span>
          </div>
          <div className="flex items-center justify-between text-slate-300">
            <span className="text-slate-400">OSM Infrastructure:</span>
            <span className="font-medium text-sky-400">301k+ Elements Cached</span>
          </div>
          <div className="flex items-center justify-between text-slate-300">
            <span className="text-slate-400">Sentinel-1 SAR:</span>
            <span className="font-medium text-amber-400">Pending Acquisition</span>
          </div>
        </div>

        {/* Action Button */}
        <div className="pt-2">
          {selectedMarker.status === 'primary_active' && selectedMarker.aoiId ? (
            <button
              onClick={() => onExploreAoi(selectedMarker.aoiId!)}
              className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-sky-600 to-indigo-600 hover:from-sky-500 hover:to-indigo-500 text-white font-bold text-xs flex items-center justify-center space-x-2 transition shadow-lg shadow-sky-950/50"
            >
              <span>Explore Flood Analysis Dashboard</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </button>
          ) : (
            <button
              onClick={() => {
                const trishuli = markers.find((m) => m.id === 'trishuli_nepal');
                if (trishuli) {
                  onSelectMarker(trishuli);
                  flyTo(trishuli.lat, trishuli.lon, 1.45);
                }
              }}
              className="w-full py-2 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold flex items-center justify-center space-x-1.5 transition"
            >
              <span>Switch to Active Trishuli Case Study</span>
            </button>
          )}
        </div>
      </div>

      {/* Attribution & Legal Notice (Bottom Right) */}
      <div className="absolute bottom-4 right-4 z-10 bg-slate-900/80 backdrop-blur px-2.5 py-1 rounded-md border border-slate-800 text-[9px] text-slate-400">
        Globe imagery: NASA Visible Earth Blue Marble. Terrain: Copernicus DEM GLO-30.
      </div>
    </div>
  );
};
