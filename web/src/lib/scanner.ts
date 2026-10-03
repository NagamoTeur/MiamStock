/* Décodage de code-barres depuis le flux caméra.
 *
 * Deux moteurs derrière la même interface :
 *  1. `BarcodeDetector`, natif sur Chrome/Android — décodage matériel, aucun
 *     octet de JavaScript à télécharger, et nettement plus tolérant sur les
 *     emballages froissés.
 *  2. ZXing en WASM/JS, chargé à la demande, pour Safari iOS qui n'implémente
 *     toujours pas `BarcodeDetector`.
 *
 * Rappel qui explique la moitié des bugs de scan en self-hosted : `getUserMedia`
 * n'existe que dans un contexte sécurisé (HTTPS, ou localhost). En http:// sur
 * une IP de LAN, `navigator.mediaDevices` est carrément `undefined`.
 */

const FORMATS = ['ean_13', 'ean_8', 'upc_a', 'upc_e', 'code_128', 'itf'] as const;

export type ScanEngine = 'native' | 'zxing';

export interface ScanSession {
  readonly engine: ScanEngine;
  stop(): void;
}

export function cameraAvailable(): boolean {
  return Boolean(navigator.mediaDevices?.getUserMedia);
}

export function secureContextOk(): boolean {
  return window.isSecureContext;
}

async function nativeDetector(): Promise<any | null> {
  const Detector = (window as any).BarcodeDetector;
  if (!Detector) return null;
  try {
    const supported: string[] = await Detector.getSupportedFormats();
    const usable = FORMATS.filter((format) => supported.includes(format));
    // Sans EAN-13, le détecteur natif ne sert à rien pour de l'alimentaire.
    if (!usable.includes('ean_13')) return null;
    return new Detector({ formats: usable });
  } catch {
    return null;
  }
}

export async function openCamera(video: HTMLVideoElement): Promise<MediaStream> {
  if (!cameraAvailable()) {
    throw new Error(
      window.isSecureContext
        ? "Aucune caméra accessible sur cet appareil."
        : "La caméra exige une connexion sécurisée (HTTPS). En http:// sur une IP locale, le navigateur la bloque.",
    );
  }
  const stream = await navigator.mediaDevices.getUserMedia({
    video: {
      facingMode: { ideal: 'environment' },
      width: { ideal: 1280 },
      height: { ideal: 720 },
    },
    audio: false,
  });
  video.srcObject = stream;
  video.setAttribute('playsinline', 'true');
  await video.play();
  return stream;
}

/**
 * Démarre la détection et appelle `onCode` à chaque lecture.
 * L'appelant garde la responsabilité de l'anti-rebond métier ; ici on se limite
 * à ne pas répéter le même code plus d'une fois par seconde.
 */
export async function startScanning(
  video: HTMLVideoElement,
  onCode: (code: string) => void,
): Promise<ScanSession> {
  let stopped = false;
  let lastCode = '';
  let lastAt = 0;

  const emit = (raw: string) => {
    const code = raw.replace(/\D/g, '');
    if (code.length < 8) return;
    const now = Date.now();
    if (code === lastCode && now - lastAt < 1200) return;
    lastCode = code;
    lastAt = now;
    onCode(code);
  };

  const detector = await nativeDetector();

  if (detector) {
    const tick = async () => {
      if (stopped) return;
      try {
        const found = await detector.detect(video);
        if (found?.length) emit(String(found[0].rawValue ?? ''));
      } catch {
        /* Une frame illisible n'est pas une erreur : on retente à la suivante. */
      }
      if (!stopped) requestAnimationFrame(() => void tick());
    };
    void tick();
    return {
      engine: 'native',
      stop() {
        stopped = true;
      },
    };
  }

  // Fallback : ZXing n'est téléchargé que sur les navigateurs qui en ont besoin.
  const { BrowserMultiFormatReader } = await import('@zxing/browser');
  const { DecodeHintType, BarcodeFormat } = await import('@zxing/library');
  const hints = new Map();
  hints.set(DecodeHintType.POSSIBLE_FORMATS, [
    BarcodeFormat.EAN_13,
    BarcodeFormat.EAN_8,
    BarcodeFormat.UPC_A,
    BarcodeFormat.UPC_E,
    BarcodeFormat.CODE_128,
    BarcodeFormat.ITF,
  ]);
  const reader = new BrowserMultiFormatReader(hints, { delayBetweenScanAttempts: 180 });
  const controls = await reader.decodeFromVideoElement(video, (result) => {
    if (result) emit(result.getText());
  });

  return {
    engine: 'zxing',
    stop() {
      stopped = true;
      controls.stop();
    },
  };
}

/** Les erreurs de getUserMedia arrivent en anglais, et dans le jargon du navigateur. */
export function messageCamera(error: unknown): string {
  const nom = (error as DOMException)?.name;
  switch (nom) {
    case 'NotAllowedError':
    case 'SecurityError':
      return "L'accès à la caméra est refusé. Autorise-le dans les réglages du navigateur, ou tape le code.";
    case 'NotFoundError':
    case 'OverconstrainedError':
      return 'Aucune caméra trouvée sur cet appareil. Tape le code à la place.';
    case 'NotReadableError':
    case 'AbortError':
      return 'La caméra est occupée par une autre application.';
    default:
      return (error as Error)?.message || "La caméra n'a pas pu s'ouvrir.";
  }
}

export function closeCamera(stream: MediaStream | null): void {
  stream?.getTracks().forEach((track) => track.stop());
}

/** Bip court en WebAudio : un retour sonore évite de regarder l'écran à chaque scan. */
export function beep(ok = true): void {
  try {
    const Ctx = window.AudioContext ?? (window as any).webkitAudioContext;
    if (!Ctx) return;
    const ctx = new Ctx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.value = ok ? 880 : 300;
    gain.gain.setValueAtTime(0.12, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.18);
    osc.connect(gain).connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.2);
    osc.onended = () => void ctx.close();
  } catch {
    /* Pas de son disponible : sans conséquence. */
  }
}

export function vibrate(pattern: number | number[] = 40): void {
  navigator.vibrate?.(pattern);
}
