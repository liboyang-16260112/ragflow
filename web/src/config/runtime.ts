import { parseEmbeddedConfig, resolvePublicAssetUrl } from './embed-config';

export const RuntimeConfig = parseEmbeddedConfig(import.meta.env);

export const publicAssetUrl = (assetPath: string): string =>
  resolvePublicAssetUrl(assetPath, RuntimeConfig.basePath);
