// TypeScript declarations for Tauri environment detection
declare global {
  interface Window {
    __TAURI__?: {
      // Tauri API modules
      [key: string]: unknown;
    };
  }
}

export {};
