import { useEffect, useRef, useState } from 'react';
import { ActionIcon, Alert, Button, Group, Loader, Modal, Stack, Text } from '@mantine/core';
import { IconBolt, IconBoltOff } from '@tabler/icons-react';
import { createDetector } from '../lib/barcodeDetector';

const SCAN_INTERVAL_MS = 150;
const CONFIRMATIONS = 2; // gleicher Code muss zweimal hintereinander gelesen werden

function cameraError(err: unknown): string {
  if (!window.isSecureContext) return 'Die Kamera ist nur über HTTPS verfügbar.';
  if (err instanceof DOMException) {
    if (err.name === 'NotAllowedError')
      return 'Der Kamerazugriff wurde verweigert. Bitte in den Browser-Einstellungen erlauben.';
    if (err.name === 'NotFoundError' || err.name === 'OverconstrainedError')
      return 'Es wurde keine Kamera gefunden.';
    if (err.name === 'NotReadableError') return 'Die Kamera wird gerade von einer anderen App verwendet.';
  }
  return 'Die Kamera konnte nicht gestartet werden.';
}

/** Kamera-Scanner für Barcodes (FR-PRD-002). Liefert den erkannten Code und schließt. */
export function BarcodeScanner({
  opened,
  onClose,
  onDetected,
}: {
  opened: boolean;
  onClose: () => void;
  onDetected: (code: string) => void;
}) {
  return (
    <Modal opened={opened} onClose={onClose} title="Barcode scannen" fullScreen radius={0} padding="sm">
      {opened && <ScannerView onDetected={onDetected} onClose={onClose} />}
    </Modal>
  );
}

function ScannerView({ onDetected, onClose }: { onDetected: (code: string) => void; onClose: () => void }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(true);
  const [torch, setTorch] = useState<{ available: boolean; on: boolean }>({ available: false, on: false });
  const trackRef = useRef<MediaStreamTrack | null>(null);

  useEffect(() => {
    let stream: MediaStream | null = null;
    let timer: number | undefined;
    let stopped = false;
    let last = '';
    let hits = 0;

    (async () => {
      try {
        if (!navigator.mediaDevices?.getUserMedia) throw new Error('unsupported');
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 }, height: { ideal: 720 } },
          audio: false,
        });
        if (stopped) return;
        const video = videoRef.current!;
        video.srcObject = stream;
        await video.play();
        const track = stream.getVideoTracks()[0];
        trackRef.current = track;
        const caps = (track.getCapabilities?.() ?? {}) as { torch?: boolean };
        setTorch({ available: !!caps.torch, on: false });
        const detector = await createDetector();
        setStarting(false);

        const tick = async () => {
          if (stopped) return;
          try {
            if (video.readyState >= 2) {
              const [hit] = await detector.detect(video);
              if (hit?.rawValue) {
                hits = hit.rawValue === last ? hits + 1 : 1;
                last = hit.rawValue;
                if (hits >= CONFIRMATIONS) {
                  stopped = true;
                  navigator.vibrate?.(60);
                  onDetected(hit.rawValue);
                  return;
                }
              }
            }
          } catch {
            // einzelne Fehlversuche ignorieren
          }
          timer = window.setTimeout(tick, SCAN_INTERVAL_MS);
        };
        tick();
      } catch (err) {
        setError(cameraError(err));
        setStarting(false);
      }
    })();

    return () => {
      stopped = true;
      window.clearTimeout(timer);
      stream?.getTracks().forEach((t) => t.stop());
    };
  }, [onDetected]);

  const toggleTorch = async () => {
    const next = !torch.on;
    try {
      await trackRef.current?.applyConstraints({ advanced: [{ torch: next } as MediaTrackConstraintSet] });
      setTorch((t) => ({ ...t, on: next }));
    } catch {
      setTorch({ available: false, on: false });
    }
  };

  return (
    <Stack>
      {error ? (
        <Alert color="red" title="Kamera nicht verfügbar">
          <Stack gap="xs">
            <Text size="sm">{error}</Text>
            <Text size="sm">Der Barcode kann auch über die Tastatur eingegeben werden.</Text>
            <Button variant="default" onClick={onClose}>
              Schließen
            </Button>
          </Stack>
        </Alert>
      ) : (
        <>
          <div style={{ position: 'relative', background: '#000', borderRadius: 8, overflow: 'hidden' }}>
            <video
              ref={videoRef}
              playsInline
              muted
              style={{ width: '100%', display: 'block', maxHeight: '70dvh', objectFit: 'cover' }}
              aria-label="Kamerabild"
            />
            {/* Zielrahmen */}
            <div
              style={{
                position: 'absolute',
                left: '10%',
                right: '10%',
                top: '35%',
                height: '30%',
                border: '3px solid rgba(255,255,255,0.85)',
                borderRadius: 8,
                boxShadow: '0 0 0 9999px rgba(0,0,0,0.35)',
              }}
            />
            {starting && (
              <Loader color="white" style={{ position: 'absolute', top: '45%', left: 'calc(50% - 18px)' }} />
            )}
          </div>
          <Group justify="space-between">
            <Text size="sm" c="dimmed">
              Barcode in den Rahmen halten.
            </Text>
            {torch.available && (
              <ActionIcon variant="light" size="xl" onClick={toggleTorch} aria-label="Taschenlampe">
                {torch.on ? <IconBoltOff /> : <IconBolt />}
              </ActionIcon>
            )}
          </Group>
          <Button variant="default" onClick={onClose}>
            Abbrechen
          </Button>
        </>
      )}
    </Stack>
  );
}
