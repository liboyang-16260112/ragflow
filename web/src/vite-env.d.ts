/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_BASE_URL?: string;
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_EMBEDDED_AUTH?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
