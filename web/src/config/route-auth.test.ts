import { resolveProtectedRouteRedirect } from './route-auth';

describe('resolveProtectedRouteRedirect', () => {
  it('redirects an unauthenticated standalone request to RAGFlow login', () => {
    expect(
      resolveProtectedRouteRedirect({
        embeddedAuth: false,
        authorization: '',
      }),
    ).toBe('/login');
  });

  it('allows an authenticated standalone request', () => {
    expect(
      resolveProtectedRouteRedirect({
        embeddedAuth: false,
        authorization: 'Bearer standalone-token',
      }),
    ).toBeNull();
  });

  it('allows a proxy-protected embedded request without browser credentials', () => {
    expect(
      resolveProtectedRouteRedirect({
        embeddedAuth: true,
        authorization: '',
      }),
    ).toBeNull();
  });
});
