export type EmbeddedEnvironment = {
  VITE_BASE_URL?: string;
  VITE_API_BASE_URL?: string;
  VITE_EMBEDDED_AUTH?: string;
};

export type EmbeddedConfig = {
  basePath: string;
  apiBasePath: string;
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
  apiBasePath: normalizeBasePath(environment.VITE_API_BASE_URL),
  embeddedAuth: environment.VITE_EMBEDDED_AUTH === 'true',
});

export const resolvePublicAssetUrl = (
  assetPath: string,
  basePath: string,
): string => `${normalizeBasePath(basePath)}${assetPath.replace(/^\/+/, '')}`;


const isAbsoluteUrl = (value: string): boolean =>
  /^[a-z][a-z\d+.-]*:\/\//i.test(value) || value.startsWith('//');

export const resolveApiUrl = (requestUrl: string, apiBasePath: string): string => {
  if (!requestUrl || isAbsoluteUrl(requestUrl)) {
    return requestUrl;
  }

  const normalizedBasePath = normalizeBasePath(apiBasePath);
  if (normalizedBasePath === '/') {
    return requestUrl.startsWith('/') ? requestUrl : `/${requestUrl}`;
  }

  if (requestUrl.startsWith(normalizedBasePath)) {
    return requestUrl;
  }

  return `${normalizedBasePath}${requestUrl.replace(/^\/+/, '')}`;
};
