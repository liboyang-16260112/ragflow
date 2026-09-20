import { RagflowStorageKey } from '@/constants/authorization';
import {
  createAuthorizationStorage,
  resolveAuthorization,
  resolveLoginRedirect,
} from './authorization-util';

describe('RAGFlow credential storage', () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem('Authorization', 'qkq-authorization');
    localStorage.setItem('token', 'qkq-token');
    localStorage.setItem('userInfo', '{"name":"QKQ user"}');
  });

  it('does not read QKQ legacy keys', () => {
    const storage = createAuthorizationStorage(localStorage);

    expect(storage.getAuthorization()).toBeNull();
    expect(storage.getToken()).toBeNull();
    expect(storage.getUserInfo()).toBeNull();
  });

  it('writes credentials only to the RAGFlow namespace', () => {
    const storage = createAuthorizationStorage(localStorage);

    storage.setCredentials({
      authorization: 'ragflow-authorization',
      token: 'ragflow-token',
      userInfo: { name: 'RAGFlow user' },
    });

    expect(localStorage.getItem(RagflowStorageKey.Authorization)).toBe(
      'ragflow-authorization',
    );
    expect(localStorage.getItem(RagflowStorageKey.Token)).toBe('ragflow-token');
    expect(localStorage.getItem(RagflowStorageKey.UserInfo)).toBe(
      '{"name":"RAGFlow user"}',
    );
    expect(localStorage.getItem('Authorization')).toBe('qkq-authorization');
    expect(localStorage.getItem('token')).toBe('qkq-token');
    expect(localStorage.getItem('userInfo')).toBe('{"name":"QKQ user"}');
  });

  it('removes only namespaced credentials', () => {
    localStorage.setItem(
      RagflowStorageKey.Authorization,
      'ragflow-authorization',
    );
    localStorage.setItem(RagflowStorageKey.Token, 'ragflow-token');
    localStorage.setItem(RagflowStorageKey.UserInfo, 'ragflow-user');
    const storage = createAuthorizationStorage(localStorage);

    storage.removeAll();

    expect(localStorage.getItem(RagflowStorageKey.Authorization)).toBeNull();
    expect(localStorage.getItem(RagflowStorageKey.Token)).toBeNull();
    expect(localStorage.getItem(RagflowStorageKey.UserInfo)).toBeNull();
    expect(localStorage.getItem('Authorization')).toBe('qkq-authorization');
    expect(localStorage.getItem('token')).toBe('qkq-token');
    expect(localStorage.getItem('userInfo')).toBe('{"name":"QKQ user"}');
  });

  it('stores thinking preference in the RAGFlow namespace even in embedded mode', () => {
    const storage = createAuthorizationStorage(localStorage, false);

    storage.setThinkingLevel('2');

    expect(storage.getThinkingLevel()).toBe('2');
    expect(localStorage.getItem(RagflowStorageKey.ThinkingLevel)).toBe('2');
    expect(localStorage.getItem('thinkingLevel')).toBeNull();
  });

  it('keeps the thinking preference when credentials are removed', () => {
    const storage = createAuthorizationStorage(localStorage);
    storage.setThinkingLevel('3');
    storage.setCredentials({
      authorization: 'ragflow-authorization',
      token: 'ragflow-token',
      userInfo: { name: 'RAGFlow user' },
    });

    storage.removeAll();

    expect(storage.getThinkingLevel()).toBe('3');
  });

  it('does not persist credentials in embedded mode', () => {
    const storage = createAuthorizationStorage(localStorage, false);

    storage.setAuthorization('real-authorization');
    storage.setToken('real-token');
    storage.setUserInfo({ name: 'Shared RAGFlow user' });
    storage.setCredentials({
      authorization: 'another-real-authorization',
      token: 'another-real-token',
      userInfo: { name: 'Another shared user' },
    });

    expect(localStorage.getItem(RagflowStorageKey.Authorization)).toBeNull();
    expect(localStorage.getItem(RagflowStorageKey.Token)).toBeNull();
    expect(localStorage.getItem(RagflowStorageKey.UserInfo)).toBeNull();
    expect(localStorage.getItem('Authorization')).toBe('qkq-authorization');
    expect(localStorage.getItem('token')).toBe('qkq-token');
    expect(localStorage.getItem('userInfo')).toBe('{"name":"QKQ user"}');
  });
});

describe('embedded request authentication', () => {
  it('uses only the fixed proxy marker in embedded mode', () => {
    expect(
      resolveAuthorization({
        embeddedAuth: true,
        searchAuthorization: 'url-secret',
        storedAuthorization: 'stored-secret',
      }),
    ).toBe('Bearer ragflow-embedded-proxy');
  });

  it('keeps standalone URL and stored credential behavior', () => {
    expect(
      resolveAuthorization({
        embeddedAuth: false,
        searchAuthorization: 'url-token',
        storedAuthorization: 'stored-token',
      }),
    ).toBe('Bearer url-token');
    expect(
      resolveAuthorization({
        embeddedAuth: false,
        searchAuthorization: null,
        storedAuthorization: 'stored-token',
      }),
    ).toBe('stored-token');
  });

  it('does not redirect embedded 401 or logout flows to RAGFlow login', () => {
    expect(
      resolveLoginRedirect({
        embeddedAuth: true,
        basePath: '/ragflow/',
        origin: 'https://qkq.example.test',
      }),
    ).toBeNull();
  });

  it('redirects standalone flows to the configured RAGFlow login path', () => {
    expect(
      resolveLoginRedirect({
        embeddedAuth: false,
        basePath: '/',
        origin: 'https://ragflow.example.test',
      }),
    ).toBe('https://ragflow.example.test/login');
  });
});
