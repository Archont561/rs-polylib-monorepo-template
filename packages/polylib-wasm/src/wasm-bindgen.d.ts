declare module "*/wasm/polylib_wasm.js" {
  /** wasm-bindgen `--target web` initializer: fetches or accepts the module. */
  export default function init(
    input?: URL | string | Request | Response | BufferSource | WebAssembly.Module,
  ): Promise<unknown>;
  export function initSync(module: { module: BufferSource | WebAssembly.Module }): unknown;
  export function wasmVersion(): string;
  export function wasmNormalizeSlug(input: string): string;
  export function wasmSummarizeScores(values: Float64Array): {
    count: number;
    min: number;
    max: number;
    mean: number;
    total: number;
  };
}
