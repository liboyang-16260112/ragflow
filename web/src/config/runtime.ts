import {
  parseEmbeddedConfig,
  resolveApiUrl,
  resolvePublicAssetUrl,
} from './embed-config';

export const RuntimeConfig = parseEmbeddedConfig(import.meta.env);

export const publicAssetUrl = (assetPath: string): string =>
  resolvePublicAssetUrl(assetPath, RuntimeConfig.basePath);

export const apiUrl = (requestUrl: string): string =>
  resolveApiUrl(requestUrl, RuntimeConfig.apiBasePath);
