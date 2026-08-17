import { parseEmbeddedConfig, resolvePublicAssetUrl } from './embed-config';

describe('parseEmbeddedConfig', () => {
  it('uses standalone defaults when the runtime has no Vite environment', () => {
    expect(parseEmbeddedConfig(undefined)).toEqual({
      basePath: '/',
      embeddedAuth: false,
    });
  });

  it('enables QKQ embedded mode with a normalized subpath', () => {
    expect(
      parseEmbeddedConfig({
        VITE_BASE_URL: '/ragflow',
        VITE_EMBEDDED_AUTH: 'true',
      }),
    ).toEqual({
      basePath: '/ragflow/',
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
