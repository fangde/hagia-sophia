import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { Water } from 'three/addons/objects/Water.js';
import './style.css';

const isMobile = window.innerWidth < 720;
const canvas = document.querySelector('#scene');
const loaderEl = document.querySelector('#loader');
const barEl = document.querySelector('#bar');
const statusEl = document.querySelector('#status');

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, isMobile ? 1.6 : 1.75));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 0.9;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x2d2438, 0.00072);

const camera = new THREE.PerspectiveCamera(window.innerWidth < 720 ? 44 : 33, window.innerWidth / window.innerHeight, 0.1, 7000);
camera.position.set(-130, -9, 340);

const controls = new OrbitControls(camera, canvas);
controls.target.set(0, 20, 0);
controls.enableDamping = true;
controls.dampingFactor = 0.055;
controls.minDistance = 55;
controls.maxDistance = 720;
controls.minPolarAngle = 0.22;
controls.maxPolarAngle = Math.PI * 0.493;
controls.panSpeed = 0.55;
controls.rotateSpeed = 0.55;
controls.zoomSpeed = 0.7;
controls.update();

// ---------------------------------------------------------------- textures
function rngFactory(seed) {
  let s = seed >>> 0;
  return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
}

function makeAshlar() {
  const S = 1024;
  const c = document.createElement('canvas'); c.width = c.height = S;
  const b = document.createElement('canvas'); b.width = b.height = S;
  const g = c.getContext('2d'); const gb = b.getContext('2d');
  const rnd = rngFactory(17);
  g.fillStyle = '#6f604e'; g.fillRect(0, 0, S, S);
  gb.fillStyle = '#5a5a5a'; gb.fillRect(0, 0, S, S);
  const rows = 8, rh = S / rows;
  for (let r = 0; r < rows; r++) {
    const y = r * rh;
    let x = (r % 2) ? -rh * 0.9 : 0;
    while (x < S) {
      const w = rh * (1.35 + rnd() * 1.35);
      const pal = ['#c0ad90', '#cdbb9f', '#b7a486', '#d4c3a6', '#ac9a7d'];
      g.fillStyle = pal[(rnd() * pal.length) | 0];
      g.fillRect(x + 2, y + 2, w - 4, rh - 4);
      g.fillStyle = 'rgba(255,255,255,.035)';
      g.fillRect(x + 2, y + 2, w - 4, 3);
      g.fillStyle = 'rgba(0,0,0,.035)';
      g.fillRect(x + 2, y + rh - 6, w - 4, 4);
      gb.fillStyle = `rgb(${170 + (rnd() * 25) | 0},${170 + (rnd() * 25) | 0},${170 + (rnd() * 25) | 0})`;
      gb.fillRect(x + 3, y + 3, w - 6, rh - 6);
      x += w;
    }
  }
  // weathering specks
  for (let i = 0; i < 9000; i++) {
    const x = rnd() * S, y = rnd() * S;
    g.fillStyle = rnd() > .5 ? 'rgba(30,22,16,.10)' : 'rgba(255,235,205,.065)';
    g.fillRect(x, y, 1.5, 1.5);
    gb.fillStyle = 'rgba(0,0,0,.06)';
    gb.fillRect(x, y, 1.5, 1.5);
  }
  const map = new THREE.CanvasTexture(c);
  map.colorSpace = THREE.SRGBColorSpace;
  map.wrapS = map.wrapT = THREE.RepeatWrapping;
  map.anisotropy = renderer.capabilities.getMaxAnisotropy();
  const bump = new THREE.CanvasTexture(b);
  bump.wrapS = bump.wrapT = THREE.RepeatWrapping;
  return { map, bump };
}

function makeOrganic(seed, palette, dark, light) {
  const S = 512;
  const c = document.createElement('canvas'); c.width = c.height = S;
  const b = document.createElement('canvas'); b.width = b.height = S;
  const g = c.getContext('2d'); const gb = b.getContext('2d');
  g.fillStyle = dark; g.fillRect(0, 0, S, S);
  gb.fillStyle = '#3a3a3a'; gb.fillRect(0, 0, S, S);
  const rnd = rngFactory(seed);
  for (let i = 0; i < 2600; i++) {
    const x = rnd() * S, y = rnd() * S, r = 1 + rnd() * 22;
    g.fillStyle = palette[(rnd() * palette.length) | 0];
    g.globalAlpha = 0.18 + rnd() * 0.35;
    g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill();
    gb.fillStyle = `rgba(${100 + rnd() * 120 | 0},${100 + rnd() * 120 | 0},${100 + rnd() * 120 | 0},.35)`;
    gb.beginPath(); gb.arc(x, y, r, 0, Math.PI * 2); gb.fill();
  }
  g.globalAlpha = 1; gb.globalAlpha = 1;
  for (let i = 0; i < 7000; i++) {
    const x = rnd() * S, y = rnd() * S;
    g.fillStyle = rnd() > .5 ? 'rgba(0,0,0,.08)' : 'rgba(255,255,255,.04)';
    g.fillRect(x, y, 1, 1);
    gb.fillStyle = 'rgba(0,0,0,.08)';
    gb.fillRect(x, y, 1, 1);
  }
  const map = new THREE.CanvasTexture(c);
  map.colorSpace = THREE.SRGBColorSpace;
  map.wrapS = map.wrapT = THREE.RepeatWrapping;
  map.anisotropy = renderer.capabilities.getMaxAnisotropy();
  const bump = new THREE.CanvasTexture(b);
  bump.wrapS = bump.wrapT = THREE.RepeatWrapping;
  return { map, bump };
}

function makeTiles() {
  const S = 512;
  const c = document.createElement('canvas'); c.width = c.height = S;
  const b = document.createElement('canvas'); b.width = b.height = S;
  const g = c.getContext('2d'); const gb = b.getContext('2d');
  const rnd = rngFactory(43);
  g.fillStyle = '#50241d'; g.fillRect(0, 0, S, S);
  gb.fillStyle = '#202020'; gb.fillRect(0, 0, S, S);
  const rows = 16, rh = S / rows;
  for (let r = 0; r < rows; r++) {
    const y = r * rh;
    for (let x = -rh; x < S; x += rh * 1.4) {
      const off = (r % 2) * rh * .7;
      g.fillStyle = ['#7b3a2a', '#8b4432', '#6d3125', '#9a4e39'][(rnd() * 4) | 0];
      g.beginPath(); g.arc(x + off + rh * .7, y + rh * .52, rh * .70, Math.PI, 0); g.fill();
      g.fillStyle = 'rgba(0,0,0,.18)';
      g.fillRect(x + off, y + rh - 2, rh * 1.4, 2);
      gb.fillStyle = `rgb(${130 + rnd() * 80 | 0},${130 + rnd() * 80 | 0},${130 + rnd() * 80 | 0})`;
      gb.beginPath(); gb.arc(x + off + rh * .7, y + rh * .52, rh * .70, Math.PI, 0); gb.fill();
    }
  }
  const map = new THREE.CanvasTexture(c);
  map.colorSpace = THREE.SRGBColorSpace;
  map.wrapS = map.wrapT = THREE.RepeatWrapping;
  map.anisotropy = renderer.capabilities.getMaxAnisotropy();
  const bump = new THREE.CanvasTexture(b);
  bump.wrapS = bump.wrapT = THREE.RepeatWrapping;
  return { map, bump };
}

function makeWaterNormals() {
  const S = 512;
  const c = document.createElement('canvas'); c.width = c.height = S;
  const g = c.getContext('2d');
  const img = g.createImageData(S, S);
  const data = img.data;
  const rnd = rngFactory(91);
  // random smooth-ish ripple field (tileable enough)
  for (let y = 0; y < S; y++) {
    for (let x = 0; x < S; x++) {
      const u = x / S * Math.PI * 2, v = y / S * Math.PI * 2;
      let nx = Math.sin(u * 7 + Math.sin(v * 3) * 2) * .55 + Math.sin(v * 11 + u * 2) * .25;
      let ny = Math.cos(v * 8 + Math.sin(u * 4) * 2) * .55 + Math.cos(u * 13 + v * 3) * .25;
      const nz = 1.0;
      const len = Math.hypot(nx, ny, nz);
      nx /= len; ny /= len;
      const i = (y * S + x) * 4;
      data[i] = (nx * .5 + .5) * 255;
      data[i + 1] = (ny * .5 + .5) * 255;
      data[i + 2] = (nz / len * .5 + .5) * 255;
      data[i + 3] = 255;
    }
  }
  g.putImageData(img, 0, 0);
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(5, 5);
  return t;
}

const ashlar = makeAshlar();
const grass = makeOrganic(31, ['#5b6b37', '#6d7a41', '#46562c', '#78824a', '#3c4a27', '#8b7d4c'], '#3f4a29');
const tiles = makeTiles();
const waterNormals = makeWaterNormals();

// ---------------------------------------------------------------- sky + env
const skyUniforms = {
  top: { value: new THREE.Color('#0c1430') },
  mid: { value: new THREE.Color('#3b335c') },
  horizon: { value: new THREE.Color('#d99679') },
  bottom: { value: new THREE.Color('#20222c') },
  sunDir: { value: new THREE.Vector3(-0.55, 0.055, -0.83).normalize() },
  sunColor: { value: new THREE.Color('#ffbe86') }
};
const skyMat = new THREE.ShaderMaterial({
  uniforms: skyUniforms,
  side: THREE.BackSide,
  depthWrite: false,
  fog: false,
  vertexShader: `
    varying vec3 vWorld;
    void main(){
      vec4 wp = modelMatrix * vec4(position,1.0);
      vWorld = wp.xyz;
      gl_Position = projectionMatrix * viewMatrix * wp;
    }
  `,
  fragmentShader: `
    uniform vec3 top, mid, horizon, bottom, sunColor;
    uniform vec3 sunDir;
    varying vec3 vWorld;
    void main(){
      vec3 d = normalize(vWorld);
      float h = d.y;
      vec3 col = mix(bottom, horizon, smoothstep(-0.12, 0.035, h));
      col = mix(col, mid, smoothstep(0.015, 0.20, h));
      col = mix(col, top, smoothstep(0.14, 0.82, h));
      float glow = pow(max(dot(d, sunDir), 0.0), 22.0);
      float wide = pow(max(dot(d, sunDir), 0.0), 4.0);
      col += sunColor * glow * 0.55;
      col += sunColor * wide * 0.075;
      float band = pow(1.0 - abs(h), 7.0);
      col += vec3(0.26, 0.12, 0.08) * band * 0.22;
      gl_FragColor = vec4(col, 1.0);
    }
  `
});
const sky = new THREE.Mesh(new THREE.SphereGeometry(3200, 48, 32), skyMat);
sky.renderOrder = -10;
scene.add(sky);

// stars
const starGeo = new THREE.BufferGeometry();
const starPos = [];
const sr = rngFactory(7);
for (let i = 0; i < 260; i++) {
  const phi = sr() * Math.PI * 2;
  const y = 0.18 + sr() * 0.78;
  const r = Math.sqrt(1 - y * y);
  starPos.push(Math.cos(phi) * r * 2600, y * 2600, Math.sin(phi) * r * 2600);
}
starGeo.setAttribute('position', new THREE.Float32BufferAttribute(starPos, 3));
const stars = new THREE.Points(starGeo, new THREE.PointsMaterial({
  color: 0xcdd8ff, size: 2.2, sizeAttenuation: true, transparent: true, opacity: 0.55, depthWrite: false, fog: false
}));
stars.renderOrder = -9;
scene.add(stars);

// environment (gradient equirect -> PMREM)
function makeEnvTexture() {
  const c = document.createElement('canvas'); c.width = 1024; c.height = 512;
  const g = c.getContext('2d');
  const grd = g.createLinearGradient(0, 0, 0, 512);
  grd.addColorStop(0, '#0d1733');
  grd.addColorStop(0.45, '#3d355e');
  grd.addColorStop(0.62, '#a06b72');
  grd.addColorStop(0.72, '#e0a07d');
  grd.addColorStop(0.78, '#3a2e39');
  grd.addColorStop(1, '#161821');
  g.fillStyle = grd; g.fillRect(0, 0, 1024, 512);
  const glow = g.createRadialGradient(220, 300, 0, 220, 300, 260);
  glow.addColorStop(0, 'rgba(255,196,140,.65)');
  glow.addColorStop(1, 'rgba(255,196,140,0)');
  g.fillStyle = glow; g.fillRect(0, 0, 1024, 512);
  const t = new THREE.CanvasTexture(c);
  t.mapping = THREE.EquirectangularReflectionMapping;
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}
const pmrem = new THREE.PMREMGenerator(renderer);
const envTex = makeEnvTexture();
const envRT = pmrem.fromEquirectangular(envTex);
scene.environment = envRT.texture;
envTex.dispose();

// ---------------------------------------------------------------- materials
function mat(name) {
  const key = name.replace(/^S_/, '').split('.')[0];
  const std = (color, roughness, metalness, extra = {}) => new THREE.MeshStandardMaterial({
    color, roughness, metalness, envMapIntensity: 0.75, ...extra
  });
  switch (key) {
    case 'Stone_Limestone':
      return std('#ffffff', 0.88, 0.0, { map: ashlar.map, bumpMap: ashlar.bump, bumpScale: 0.16 });
    case 'Stone_Dark':
      return std('#8d7c66', 0.94, 0.0, { map: ashlar.map, bumpMap: ashlar.bump, bumpScale: 0.14 });
    case 'Stone_Trim':
      return std('#d8c49f', 0.68, 0.0);
    case 'Marble':
      return std('#e4d9c4', 0.42, 0.0);
    case 'Marble_Red':
      return std('#74302c', 0.34, 0.0);
    case 'Marble_Green':
      return std('#2f5a43', 0.34, 0.0);
    case 'Lead_Roof':
      return std('#5f6c75', 0.36, 0.55, { envMapIntensity: 1.0 });
    case 'Lead_Ribs':
      return std('#84919a', 0.32, 0.5, { envMapIntensity: 1.0 });
    case 'Gold':
      return std('#d6a03d', 0.25, 1.0, { envMapIntensity: 1.3 });
    case 'Brass':
      return std('#b6862d', 0.32, 0.9);
    case 'Iron':
      return std('#25282b', 0.5, 0.65);
    case 'BoatWood':
    case 'PortalDoor':
      return std('#3a2416', 0.72, 0.0);
    case 'Cypress':
      return std('#1d3925', 0.92, 0.0);
    case 'Trunk':
      return std('#33251a', 0.95, 0.0);
    case 'CityStone':
      return std('#2c3035', 0.96, 0.0);
    case 'Hills':
      return std('#28313e', 0.98, 0.0);
    case 'RoofTile':
      return std('#ffffff', 0.82, 0.0, { map: tiles.map, bumpMap: tiles.bump, bumpScale: 0.10 });
    case 'Hillside':
      return std('#ffffff', 0.98, 0.0, { map: grass.map, bumpMap: grass.bump, bumpScale: 0.20 });
    case 'Window_Warm':
      return new THREE.MeshStandardMaterial({ color: 0x000000, emissive: 0xff9840, emissiveIntensity: 2.2, roughness: 1, metalness: 0, side: THREE.DoubleSide });
    case 'Window_Amber':
      return new THREE.MeshStandardMaterial({ color: 0x000000, emissive: 0xffb05c, emissiveIntensity: 1.7, roughness: 1, metalness: 0, side: THREE.DoubleSide });
    case 'Window_Dim':
      return new THREE.MeshStandardMaterial({ color: 0x000000, emissive: 0xff8a34, emissiveIntensity: 0.9, roughness: 1, metalness: 0, side: THREE.DoubleSide });
    case 'LampGlow':
      return new THREE.MeshStandardMaterial({ color: 0x000000, emissive: 0xffd08a, emissiveIntensity: 3.6, roughness: 1, metalness: 0, side: THREE.DoubleSide });
    case 'Window_Dark':
      return std('#0c141c', 0.08, 0.35);
    default:
      return std('#8e7e68', 0.85, 0.0);
  }
}

// ---------------------------------------------------------------- model
const world = new THREE.Group();
scene.add(world);
const loader = new GLTFLoader();
let ready = false;

loader.load('./assets/hagia_sophia.glb', (gltf) => {
  const root = gltf.scene;
  root.updateMatrixWorld(true);
  const groups = new Map();
  const originalMaterials = new Set();
  root.traverse((o) => {
    if (!o.isMesh) return;
    const m = Array.isArray(o.material) ? o.material[0] : o.material;
    const raw = m?.name || 'Default';
    originalMaterials.add(raw);
    let g = o.geometry.index ? o.geometry.toNonIndexed() : o.geometry.clone();
    g.applyMatrix4(o.matrixWorld);
    for (const name of Object.keys(g.attributes)) {
      if (!['position', 'normal', 'uv'].includes(name)) g.deleteAttribute(name);
    }
    if (!g.attributes.normal) g.computeVertexNormals();
    if (!g.attributes.uv) {
      g.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(g.attributes.position.count * 2), 2));
    }
    g.clearGroups();
    const key = raw.replace(/^S_/, '').split('.')[0];
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(g);
  });
  console.log('GLB materials:', [...originalMaterials].join(', '));

  function planarUV(geometry, scale) {
    const p = geometry.attributes.position;
    const n = geometry.attributes.normal;
    const uv = new Float32Array(p.count * 2);
    for (let i = 0; i < p.count; i += 3) {
      const nx = Math.abs(n.getX(i) + n.getX(i + 1) + n.getX(i + 2));
      const ny = Math.abs(n.getY(i) + n.getY(i + 1) + n.getY(i + 2));
      const nz = Math.abs(n.getZ(i) + n.getZ(i + 1) + n.getZ(i + 2));
      for (let k = 0; k < 3; k++) {
        const x = p.getX(i + k), y = p.getY(i + k), z = p.getZ(i + k);
        let u, v;
        if (ny >= nx && ny >= nz) { u = x; v = z; }
        else if (nx >= nz) { u = z; v = y; }
        else { u = x; v = y; }
        uv[(i + k) * 2] = u / scale;
        uv[(i + k) * 2 + 1] = v / scale;
      }
    }
    geometry.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
  }

  let meshCount = 0;
  for (const [key, geoms] of groups) {
    if (!geoms.length) continue;
    if (key === 'Stone_Limestone' || key === 'Stone_Dark') geoms.forEach(g => planarUV(g, 4.0));
    else if (key === 'Hillside') geoms.forEach(g => planarUV(g, 26.0));
    else if (key === 'RoofTile') geoms.forEach(g => planarUV(g, 2.6));
    let merged;
    try {
      merged = mergeGeometries(geoms, false);
    } catch (e) {
      console.warn('merge failed', key, e);
      merged = null;
    }
    const material = mat(key);
    if (merged) {
      const mesh = new THREE.Mesh(merged, material);
      mesh.castShadow = !['Window_Warm', 'Window_Amber', 'Window_Dim', 'LampGlow', 'Window_Dark'].includes(key);
      mesh.receiveShadow = !['Window_Warm', 'Window_Amber', 'Window_Dim', 'LampGlow'].includes(key);
      world.add(mesh);
      meshCount++;
      geoms.forEach(g => g.dispose?.());
    } else {
      for (const g of geoms) {
        const mesh = new THREE.Mesh(g, material);
        mesh.castShadow = mesh.receiveShadow = true;
        world.add(mesh);
        meshCount++;
      }
    }
  }
  console.log('merged draw calls:', meshCount);

  const box = new THREE.Box3().setFromObject(world);
  console.log('model bounds', box.min.toArray().map(v => v.toFixed(1)), box.max.toArray().map(v => v.toFixed(1)));

  // lighting
  scene.add(new THREE.AmbientLight(0x6f7fa0, 0.3));
  const hemi = new THREE.HemisphereLight(0x8ea4d4, 0x2a2018, 0.75);
  scene.add(hemi);

  const key = new THREE.DirectionalLight(0xffc59a, 2.8);
  key.position.set(-200, 170, 240);
  key.target.position.set(0, 20, 0);
  key.castShadow = true;
  key.shadow.mapSize.set(isMobile ? 1024 : 2048, isMobile ? 1024 : 2048);
  key.shadow.camera.left = -250; key.shadow.camera.right = 250;
  key.shadow.camera.top = 250; key.shadow.camera.bottom = -250;
  key.shadow.camera.near = 1; key.shadow.camera.far = 900;
  key.shadow.bias = -0.0004;
  key.shadow.normalBias = 0.8;
  scene.add(key, key.target);

  const rim = new THREE.DirectionalLight(0x7d9cff, 1.2);
  rim.position.set(170, 130, -260);
  rim.target.position.set(0, 25, 0);
  scene.add(rim, rim.target);

  function spot(pos, target, color, intensity, angle, penumbra = 0.7, distance = 200, shadow = false) {
    const s = new THREE.SpotLight(color, intensity, distance, angle, penumbra, 2);
    s.position.set(...pos);
    s.target.position.set(...target);
    s.castShadow = shadow;
    scene.add(s, s.target);
    return s;
  }
  spot([-30, 3, 43], [0, 24, 28], 0xffc08a, 2000, 0.55, 0.75);
  spot([30, 3, 43], [0, 24, 28], 0xffc08a, 2000, 0.55, 0.75);
  spot([0, 4, 41], [0, 18, 30], 0xffc08a, 700, 0.45, 0.7);
  spot([-18, 20, 54], [0, 46, 4], 0xffb578, 6000, 0.38, 0.6);
  spot([18, 20, 54], [0, 46, 4], 0xffb578, 6000, 0.38, 0.6);
  spot([150, 100, -180], [0, 35, 0], 0x7799ff, 8000, 0.4, 0.8);

  // stair and hillside practicals
  const practicals = [
    [6, -1, 82], [6, -4, 72], [6, -7, 62], [6, -10, 53],
    [-6, -4, 74], [-6, -8, 62],
    [-66, -5, 72], [70, -4, 66], [-100, -2, 60], [104, -3, 58]
  ];
  for (const p of practicals) {
    const l = new THREE.PointLight(0xffb36c, 180, 55, 2);
    l.position.set(...p);
    scene.add(l);
  }

  // procedural ocean: subdivided plane + custom reflected water shader
  const water = new Water(new THREE.PlaneGeometry(5200, 5200, 360, 360), {
    textureWidth: isMobile ? 512 : 1024,
    textureHeight: isMobile ? 512 : 1024,
    waterNormals,
    sunDirection: new THREE.Vector3(-0.55, 0.08, -0.83).normalize(),
    sunColor: 0xffb27a,
    waterColor: 0x10222b,
    distortionScale: 1.3,
    fog: false,
    alpha: 1.0
  });
  water.rotation.x = -Math.PI / 2;
  water.position.y = -14.0;
  scene.add(water);
  const wu = water.material.uniforms;
  wu.uSunDir = { value: new THREE.Vector3(-0.55, 0.08, -0.83).normalize() };
  wu.uSunColor = { value: new THREE.Color(0xffb27a) };
  wu.uFogColor = { value: new THREE.Color(0x2d2438) };
  wu.uFogDensity = { value: 0.00065 };
  water.material.vertexShader = /* glsl */`
    uniform mat4 textureMatrix;
    uniform float time;
    varying vec4 vMirrorCoord;
    varying vec3 vWorldPos;
    varying vec3 vNormalW;
    varying float vWave;

    void main() {
      vec4 base = modelMatrix * vec4(position, 1.0);
      vec2 p = base.xz;

      // four large directional swells
      float a1 = 1.25, a2 = 0.75, a3 = 0.40, a4 = 0.18;
      vec2 d1 = vec2(0.045, 0.022);
      vec2 d2 = vec2(-0.031, 0.061);
      vec2 d3 = vec2(0.085, -0.038);
      vec2 d4 = vec2(-0.120, -0.090);
      float ph1 = dot(p, d1) + time * 0.55;
      float ph2 = dot(p, d2) + time * 0.82;
      float ph3 = dot(p, d3) + time * 1.15;
      float ph4 = dot(p, d4) + time * 1.60;
      float h = sin(ph1) * a1 + sin(ph2) * a2 + sin(ph3) * a3 + sin(ph4) * a4;
      base.y += h;

      vWorldPos = base.xyz;
      vWave = h;
      vMirrorCoord = textureMatrix * base;

      float dhx = cos(ph1) * a1 * d1.x + cos(ph2) * a2 * d2.x +
                  cos(ph3) * a3 * d3.x + cos(ph4) * a4 * d4.x;
      float dhz = cos(ph1) * a1 * d1.y + cos(ph2) * a2 * d2.y +
                  cos(ph3) * a3 * d3.y + cos(ph4) * a4 * d4.y;
      vNormalW = normalize(vec3(-dhx * 2.2, 1.0, -dhz * 2.2));

      gl_Position = projectionMatrix * viewMatrix * base;
    }
  `;
  water.material.fragmentShader = /* glsl */`
    uniform sampler2D mirrorSampler;
    uniform float time;
    uniform float distortionScale;
    uniform float alpha;
    uniform vec3 waterColor;
    uniform vec3 uSunDir;
    uniform vec3 uSunColor;
    uniform vec3 uFogColor;
    uniform float uFogDensity;
    varying vec4 vMirrorCoord;
    varying vec3 vWorldPos;
    varying vec3 vNormalW;
    varying float vWave;

    void main() {
      vec2 p = vWorldPos.xz;

      // fine procedural ripples: analytic slopes, animated in time
      float dhx = 0.0, dhz = 0.0;
      // 3.5 m
      dhx += cos(dot(p, vec2(0.88, 0.38)) + time * 2.1) * 0.22 * 0.88;
      dhz += cos(dot(p, vec2(0.88, 0.38)) + time * 2.1) * 0.22 * 0.38;
      // 2.2 m
      dhx += cos(dot(p, vec2(-0.55, 0.95)) + time * 3.0) * 0.14 * -0.55;
      dhz += cos(dot(p, vec2(-0.55, 0.95)) + time * 3.0) * 0.14 * 0.95;
      // 1.3 m
      dhx += cos(dot(p, vec2(1.55, -1.10)) + time * 4.2) * 0.08 * 1.55;
      dhz += cos(dot(p, vec2(1.55, -1.10)) + time * 4.2) * 0.08 * -1.10;
      // 0.7 m
      dhx += cos(dot(p, vec2(-2.3, -1.7)) + time * 5.6) * 0.04 * -2.3;
      dhz += cos(dot(p, vec2(-2.3, -1.7)) + time * 5.6) * 0.04 * -1.7;

      vec3 n = normalize(vNormalW + vec3(-dhx * 0.9, 0.0, -dhz * 0.9));
      vec3 V = normalize(cameraPosition - vWorldPos);

      vec2 uv = vMirrorCoord.xy / vMirrorCoord.w;
      uv += n.xz * (0.016 * distortionScale);
      vec3 refl = texture2D(mirrorSampler, clamp(uv, 0.002, 0.998)).rgb;

      float fres = pow(1.0 - clamp(dot(n, V), 0.0, 1.0), 3.0);
      fres = clamp(0.16 + fres * 0.92, 0.0, 0.94);
      vec3 col = mix(waterColor, refl, fres);

      // sun/evening glitter
      vec3 H = normalize(uSunDir + V);
      float spec = pow(max(dot(n, H), 0.0), 240.0) * 2.4;
      col += uSunColor * spec * 0.9;

      // small crest foam
      float foam = smoothstep(1.05, 1.65, vWave) * 0.10;
      col = mix(col, vec3(0.58, 0.68, 0.72), foam);

      // atmospheric fade
      float dist = length(cameraPosition - vWorldPos);
      float fog = 1.0 - exp(-uFogDensity * uFogDensity * dist * dist);
      col = mix(col, uFogColor, clamp(fog, 0.0, 0.92));

      gl_FragColor = vec4(col, alpha);
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
    }
  `;
  water.material.needsUpdate = true;

  // post
  const composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));
  const bloom = new UnrealBloomPass(new THREE.Vector2(window.innerWidth / 2, window.innerHeight / 2), 0.25, 0.55, 0.92);
  composer.addPass(bloom);
  composer.addPass(new OutputPass());

  // views
  const views = {
    hero: { pos: [-130, -9, 340], target: [0, 20, 0] },
    front: { pos: [-5, -9, 330], target: [0, 18, 0] },
    east: { pos: [160, -8, 270], target: [0, 18, 0] },
    low: { pos: [-55, -11, 215], target: [0, 28, 0] }
  };
  let fly = null;
  function applyView(name, instant = false) {
    const v = views[name];
    if (!v) return;
    const p = new THREE.Vector3(...v.pos);
    const t = new THREE.Vector3(...v.target);
    if (instant) {
      camera.position.copy(p); controls.target.copy(t); controls.update(); return;
    }
    fly = { p0: camera.position.clone(), t0: controls.target.clone(), p1: p, t1: t, start: performance.now(), dur: 1500 };
  }
  applyView('hero', true);

  document.querySelectorAll('.view').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.view').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      applyView(btn.dataset.view);
    });
  });
  canvas.addEventListener('pointerdown', () => { fly = null; });

  const clock = new THREE.Clock();
  let first = true;
  function resize() {
    const w = window.innerWidth, h = window.innerHeight;
    camera.aspect = w / h;
    camera.fov = w < 720 ? 44 : 33;
    camera.updateProjectionMatrix();
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, isMobile ? 1.6 : 1.75));
    renderer.setSize(w, h);
    composer.setSize(w, h);
    bloom.setSize(w, h);
  }
  window.addEventListener('resize', resize);
  resize();

  function animate() {
    requestAnimationFrame(animate);
    const dt = Math.min(clock.getDelta(), 0.05);
    if (fly) {
      const t = Math.min(1, (performance.now() - fly.start) / fly.dur);
      const e = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
      camera.position.lerpVectors(fly.p0, fly.p1, e);
      controls.target.lerpVectors(fly.t0, fly.t1, e);
      if (t >= 1) fly = null;
    }
    controls.update();
    water.material.uniforms['time'].value += dt * 0.28;
    stars.rotation.y += dt * 0.0018;
    if (first) {
      first = false;
      loaderEl.classList.add('hidden');
      window.__READY__ = true;
      document.body.classList.add('ready');
    }
    composer.render();
  }
  animate();
}, (ev) => {
  if (ev.total) {
    const pct = Math.min(100, Math.round(ev.loaded / ev.total * 100));
    barEl.style.width = pct + '%';
    statusEl.textContent = pct < 100 ? `assembling stone & sea… ${pct}%` : 'lighting the hill…';
  }
}, (err) => {
  console.error('GLB load failed', err);
  statusEl.textContent = 'could not load the model';
  loaderEl.style.background = '#160d12';
});
