import { Maximize2, MousePointer2, Rotate3D, ZoomIn } from "lucide-react";
import { useEffect, useRef, type ReactNode } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

import { usePipelineStore } from "../stores/pipelineStore";
import type { Edge, GraphResponse, Position } from "../types";

export function GraphCanvas() {
  const graph = usePipelineStore((state) => state.graph);
  const job = usePipelineStore((state) => state.job);
  const mountRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) {
      return undefined;
    }

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x090d13);

    const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 1000);
    camera.position.set(0, -8, 7);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    mount.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.enablePan = true;
    controls.minDistance = 2.8;
    controls.maxDistance = 28;
    controls.target.set(0, 0, 0);

    scene.add(new THREE.AmbientLight(0xbffcf0, 0.45));

    const keyLight = new THREE.DirectionalLight(0xc7fff4, 2.2);
    keyLight.position.set(3, -5, 8);
    keyLight.castShadow = true;
    scene.add(keyLight);

    const fillLight = new THREE.PointLight(0x6ee7cf, 2.5, 24);
    fillLight.position.set(-5, 4, 5);
    scene.add(fillLight);

    const graphGroup = new THREE.Group();
    scene.add(graphGroup);

    const grid = new THREE.GridHelper(12, 12, 0x24423d, 0x172621);
    grid.rotation.x = Math.PI / 2;
    grid.position.z = -1.35;
    scene.add(grid);

    const halo = new THREE.Mesh(
      new THREE.TorusGeometry(4.3, 0.012, 16, 160),
      new THREE.MeshBasicMaterial({ color: 0x355f56, transparent: true, opacity: 0.45 }),
    );
    halo.rotation.x = Math.PI / 2;
    halo.position.z = -1.32;
    scene.add(halo);

    if (graph) {
      buildGraphScene(graphGroup, graph, job?.status === "running" || job?.status === "queued");
      frameCamera(camera, controls, graph);
    } else {
      buildEmptyScene(graphGroup);
    }

    const resize = () => {
      const { width, height } = mount.getBoundingClientRect();
      renderer.setSize(width, height, false);
      camera.aspect = width / Math.max(height, 1);
      camera.updateProjectionMatrix();
    };

    const observer = new ResizeObserver(resize);
    observer.observe(mount);
    resize();

    let animationFrame = 0;
    const clock = new THREE.Clock();

    const animate = () => {
      const elapsed = clock.getElapsedTime();
      graphGroup.rotation.z = Math.sin(elapsed * 0.22) * 0.025;

      for (const child of graphGroup.children) {
        if (child.userData.kind === "node") {
          child.scale.setScalar(1 + Math.sin(elapsed * 2.4 + child.userData.phase) * 0.035);
        }
      }

      controls.update();
      renderer.render(scene, camera);
      animationFrame = window.requestAnimationFrame(animate);
    };
    animate();

    return () => {
      window.cancelAnimationFrame(animationFrame);
      observer.disconnect();
      controls.dispose();
      mount.removeChild(renderer.domElement);
      scene.traverse((object) => {
        if (object instanceof THREE.Mesh || object instanceof THREE.Line || object instanceof THREE.Sprite) {
          object.geometry?.dispose();
          const materials = Array.isArray(object.material) ? object.material : [object.material];
          for (const material of materials) {
            disposeMaterial(material);
          }
        }
      });
      renderer.dispose();
    };
  }, [graph, job?.status]);

  return (
    <section className="relative min-h-[620px] overflow-hidden rounded-md border border-border bg-background shadow-panel">
      <div className="absolute left-5 top-5 z-10">
        <p className="text-xs font-medium uppercase text-foreground/50">3D graph canvas</p>
        <h2 className="text-2xl font-semibold">{graph ? `${graph.family} / ${graph.n_nodes} nodes` : "Generate a graph"}</h2>
      </div>

      <div className="absolute right-5 top-5 z-10 grid grid-cols-4 gap-2">
        <ControlBadge icon={<Rotate3D size={14} />} label="Drag" />
        <ControlBadge icon={<ZoomIn size={14} />} label="Zoom" />
        <ControlBadge icon={<MousePointer2 size={14} />} label="Pan" />
        <ControlBadge icon={<Maximize2 size={14} />} label="Orbit" />
      </div>

      <div ref={mountRef} className="h-full min-h-[620px] w-full" />
    </section>
  );
}

function buildGraphScene(group: THREE.Group, graph: GraphResponse, isRunning: boolean) {
  const positions = normalizedPositions(graph);
  const degree = degreeMap(graph.edges);

  for (const edge of graph.edges) {
    const source = positions.get(edge.i);
    const target = positions.get(edge.j);
    if (!source || !target) {
      continue;
    }
    group.add(createEdge(source, target, edge.w));
  }

  for (const position of graph.positions) {
    const point = positions.get(position.id);
    if (!point) {
      continue;
    }
    const node = createNode(point, isRunning, position.id);
    node.userData.kind = "node";
    node.userData.phase = position.id * 0.8;
    group.add(node);

    const label = createLabel(String(position.id));
    label.position.copy(point).add(new THREE.Vector3(0, 0, 0.38 + (degree.get(position.id) ?? 0) * 0.01));
    group.add(label);
  }
}

function buildEmptyScene(group: THREE.Group) {
  const material = new THREE.MeshStandardMaterial({
    color: 0x6ee7cf,
    emissive: 0x153b35,
    roughness: 0.38,
    metalness: 0.15,
    transparent: true,
    opacity: 0.75,
  });

  for (let i = 0; i < 6; i += 1) {
    const angle = (Math.PI * 2 * i) / 6;
    const sphere = new THREE.Mesh(new THREE.SphereGeometry(0.2, 32, 32), material.clone());
    sphere.position.set(Math.cos(angle) * 2.1, Math.sin(angle) * 2.1, Math.sin(angle * 2) * 0.55);
    sphere.userData.kind = "node";
    sphere.userData.phase = i;
    group.add(sphere);
  }
}

function normalizedPositions(graph: GraphResponse) {
  const xs = graph.positions.map((position) => position.x);
  const ys = graph.positions.map((position) => position.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const span = Math.max(maxX - minX, maxY - minY, 0.001);
  const degree = degreeMap(graph.edges);
  const maxDegree = Math.max(...Array.from(degree.values()), 1);
  const result = new Map<number, THREE.Vector3>();

  for (const position of graph.positions) {
    const x = ((position.x - (minX + maxX) / 2) / span) * 5.2;
    const y = ((position.y - (minY + maxY) / 2) / span) * 5.2;
    const degreeLift = ((degree.get(position.id) ?? 0) / maxDegree - 0.5) * 1.15;
    const orbitLift = Math.sin(position.id * 1.618) * 0.35;
    result.set(position.id, new THREE.Vector3(x, y, degreeLift + orbitLift));
  }

  return result;
}

function degreeMap(edges: Edge[]) {
  const degree = new Map<number, number>();
  for (const edge of edges) {
    degree.set(edge.i, (degree.get(edge.i) ?? 0) + 1);
    degree.set(edge.j, (degree.get(edge.j) ?? 0) + 1);
  }
  return degree;
}

function createNode(position: THREE.Vector3, isRunning: boolean, id: number) {
  const geometry = new THREE.SphereGeometry(0.22, 40, 40);
  const material = new THREE.MeshStandardMaterial({
    color: 0x78e4ca,
    emissive: isRunning ? 0x286e61 : 0x143a34,
    emissiveIntensity: isRunning ? 0.65 : 0.35,
    roughness: 0.22,
    metalness: 0.18,
  });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.position.copy(position);
  mesh.castShadow = true;
  mesh.receiveShadow = true;

  const glow = new THREE.Mesh(
    new THREE.SphereGeometry(0.34, 32, 32),
    new THREE.MeshBasicMaterial({
      color: 0x77f7da,
      transparent: true,
      opacity: isRunning ? 0.18 : 0.1,
      depthWrite: false,
    }),
  );
  glow.userData.phase = id * 0.8;
  mesh.add(glow);

  return mesh;
}

function createEdge(source: THREE.Vector3, target: THREE.Vector3, weight: number) {
  const geometry = new THREE.BufferGeometry().setFromPoints([source, target]);
  const material = new THREE.LineBasicMaterial({
    color: 0x6ee7cf,
    transparent: true,
    opacity: Math.min(0.92, 0.28 + weight / 3.5),
  });
  const line = new THREE.Line(geometry, material);

  const midpoint = source.clone().add(target).multiplyScalar(0.5);
  const bead = new THREE.Mesh(
    new THREE.SphereGeometry(0.035 + Math.min(weight, 3) * 0.012, 18, 18),
    new THREE.MeshBasicMaterial({ color: 0xc8fff3, transparent: true, opacity: 0.65 }),
  );
  bead.position.copy(midpoint);

  const edgeGroup = new THREE.Group();
  edgeGroup.add(line, bead);
  return edgeGroup;
}

function createLabel(text: string) {
  const canvas = document.createElement("canvas");
  canvas.width = 128;
  canvas.height = 128;
  const context = canvas.getContext("2d");
  if (context) {
    context.clearRect(0, 0, canvas.width, canvas.height);
    context.fillStyle = "rgba(8, 13, 19, 0.72)";
    context.beginPath();
    context.arc(64, 64, 42, 0, Math.PI * 2);
    context.fill();
    context.fillStyle = "#d6fff4";
    context.font = "700 48px Inter, Arial, sans-serif";
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.fillText(text, 64, 66);
  }
  const texture = new THREE.CanvasTexture(canvas);
  const material = new THREE.SpriteMaterial({ map: texture, transparent: true, depthWrite: false });
  const sprite = new THREE.Sprite(material);
  sprite.scale.set(0.5, 0.5, 0.5);
  return sprite;
}

function frameCamera(camera: THREE.PerspectiveCamera, controls: OrbitControls, graph: GraphResponse) {
  const count = Math.max(graph.positions.length, 2);
  const distance = Math.min(20, Math.max(8.5, count * 1.15));
  camera.position.set(0, -distance, distance * 0.78);
  controls.target.set(0, 0, 0);
  controls.update();
}

function disposeMaterial(material: THREE.Material) {
  for (const value of Object.values(material)) {
    if (value && typeof value === "object" && "dispose" in value && typeof value.dispose === "function") {
      value.dispose();
    }
  }
  material.dispose();
}

function ControlBadge({ icon, label }: { icon: ReactNode; label: string }) {
  return (
    <div className="flex h-9 min-w-16 items-center justify-center gap-1 rounded-md border border-border bg-background/80 px-2 text-xs text-foreground/70 backdrop-blur">
      <span className="text-primary">{icon}</span>
      <span>{label}</span>
    </div>
  );
}
