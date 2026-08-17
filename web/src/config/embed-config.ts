export type EmbeddedEnvironment = {
  VITE_BASE_URL?: string;
  VITE_EMBEDDED_AUTH?: string;
};

export type EmbeddedConfig = {
  basePath: string;
  embeddedAuth: boolean;
};

const normalizeBasePath = (value: string | undefined): string => {
  const trimmed = value?.trim();
  if (!trimmed || trimmed === '/') {
    return '/';
  }

  return `/${trimmed.replace(/^\/+|\/+$/g, '')}/`;
};

export const parseEmbeddedConfig = (
  environment: EmbeddedEnvironment = {},
): EmbeddedConfig => ({
  basePath: normalizeBasePath(environment.VITE_BASE_URL),
  embeddedAuth: environment.VITE_EMBEDDED_AUTH === 'true',
});

export const resolvePublicAssetUrl = (
  assetPath: string,
  basePath: string,
): string => `${normalizeBasePath(basePath)}${assetPath.replace(/^\/+/, '')}`;
