import {
  parseEmbeddedConfig,
  resolveApiUrl,
  resolvePublicAssetUrl,
} from './embed-config';

const browserRuntimeConfig =
  typeof window === 'undefined' ? undefined : window.__RAGFLOW_RUNTIME_CONFIG__;

export const RuntimeConfig = parseEmbeddedConfig(
  import.meta.env,
  browserRuntimeConfig,
);

export const publicAssetUrl = (assetPath: string): string =>
  resolvePublicAssetUrl(assetPath, RuntimeConfig.basePath);

export const apiUrl = (requestUrl: string): string =>
  resolveApiUrl(requestUrl, RuntimeConfig.apiBasePath);
