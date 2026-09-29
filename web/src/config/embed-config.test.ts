import {
  parseEmbeddedConfig,
  resolveApiUrl,
  resolvePublicAssetUrl,
} from './embed-config';

describe('parseEmbeddedConfig', () => {
  it('uses standalone defaults when the runtime has no Vite environment', () => {
    expect(parseEmbeddedConfig(undefined)).toEqual({
      basePath: '/',
      apiBasePath: '/',
      embeddedAuth: false,
    });
  });

  it('lets a standalone listener disable embedded authentication at runtime', () => {
    expect(
      parseEmbeddedConfig(
        {
          VITE_BASE_URL: '/ragflow',
          VITE_API_BASE_URL: '/ragflow-api',
          VITE_EMBEDDED_AUTH: 'true',
        },
        { embeddedAuth: false },
      ),
    ).toEqual({
      basePath: '/ragflow/',
      apiBasePath: '/ragflow-api/',
      embeddedAuth: false,
    });
  });

  it('keeps the build-time authentication mode without a runtime override', () => {
    expect(parseEmbeddedConfig({ VITE_EMBEDDED_AUTH: 'true' })).toMatchObject({
      embeddedAuth: true,
    });
  });

  it('enables QKQ embedded mode with a normalized subpath', () => {
    expect(
      parseEmbeddedConfig({
        VITE_BASE_URL: '/ragflow',
        VITE_EMBEDDED_AUTH: 'true',
        VITE_API_BASE_URL: '/ragflow-api',
      }),
    ).toEqual({
      basePath: '/ragflow/',
      apiBasePath: '/ragflow-api/',
      embeddedAuth: true,
    });
  });

  it.each([undefined, '', 'false', '1', 'TRUE'])(
    'keeps embedded authentication disabled for %p',
    (value) => {
      expect(
        parseEmbeddedConfig({
          VITE_BASE_URL: '/',
          VITE_EMBEDDED_AUTH: value,
        }),
      ).toEqual({
        basePath: '/',
        apiBasePath: '/',
        embeddedAuth: false,
      });
    },
  );

  it('adds the configured base path to public assets', () => {
    expect(resolvePublicAssetUrl('/fmoss-logo.png', '/ragflow/')).toBe(
      '/ragflow/fmoss-logo.png',
    );
  });
});

describe('resolveApiUrl', () => {
  it('routes embedded API requests through the dedicated ingress prefix', () => {
    expect(resolveApiUrl('/api/v1/providers', '/ragflow-api/')).toBe(
      '/ragflow-api/api/v1/providers',
    );
    expect(resolveApiUrl('/v1/llm/list', '/ragflow-api')).toBe(
      '/ragflow-api/v1/llm/list',
    );
    expect(
      resolveApiUrl('https://example.test/api/v1/models', '/ragflow-api'),
    ).toBe('https://example.test/api/v1/models');
  });
});
