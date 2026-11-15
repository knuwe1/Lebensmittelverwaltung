/**
 * Barcode-Erkennung (FR-PRD-002): EAN-13, EAN-8, UPC-A.
 *
 * Nutzt die native Shape-Detection-API (Chrome auf Android), sonst einen WebAssembly-
 * Ersatz (zxing-wasm). Die .wasm-Datei wird von der eigenen Instanz ausgeliefert –
 * kein Nachladen von fremden Servern (Datenschutz, CSP).
 */
import { BarcodeDetector as ZXingDetector, prepareZXingModule } from 'barcode-detector/ponyfill';
import wasmUrl from 'zxing-wasm/reader/zxing_reader.wasm?url';

export const FORMATS = ['ean_13', 'ean_8', 'upc_a'] as const;

export interface Detector {
  detect(source: CanvasImageSource | Blob | ImageData): Promise<{ rawValue: string; format: string }[]>;
}

let prepared = false;

interface NativeDetectorClass {
  new (opts: { formats: string[] }): Detector;
  getSupportedFormats(): Promise<string[]>;
}

export async function createDetector(): Promise<Detector> {
  const Native = (window as unknown as { BarcodeDetector?: NativeDetectorClass }).BarcodeDetector;
  if (Native) {
    try {
      const supported = await Native.getSupportedFormats();
      const formats = FORMATS.filter((f) => supported.includes(f));
      if (formats.length === FORMATS.length) return new Native({ formats });
    } catch {
      // auf WebAssembly ausweichen
    }
  }
  if (!prepared) {
    prepareZXingModule({
      overrides: {
        locateFile: (path: string, prefix: string) => (path.endsWith('.wasm') ? wasmUrl : prefix + path),
      },
    });
    prepared = true;
  }
  return new ZXingDetector({ formats: [...FORMATS] });
}
