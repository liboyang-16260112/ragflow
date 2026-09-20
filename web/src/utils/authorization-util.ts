/*
 *  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */

import { RagflowStorageKey } from '@/constants/authorization';
import { RuntimeConfig } from '@/config/runtime';
import { getSearchValue } from './common-util';

const CredentialKeySet = [
  RagflowStorageKey.Authorization,
  RagflowStorageKey.Token,
  RagflowStorageKey.UserInfo,
];

type CredentialSet = {
  authorization: string;
  token: string;
  userInfo: string | Record<string, unknown>;
};

export const createAuthorizationStorage = (
  browserStorage: Storage,
  persistCredentials = true,
) => ({
  getAuthorization: () => {
    return browserStorage.getItem(RagflowStorageKey.Authorization);
  },
  getToken: () => {
    return browserStorage.getItem(RagflowStorageKey.Token);
  },
  getUserInfo: () => {
    return browserStorage.getItem(RagflowStorageKey.UserInfo);
  },
  getUserInfoObject: () => {
    const userInfoStr = browserStorage.getItem(RagflowStorageKey.UserInfo);
    return userInfoStr ? JSON.parse(userInfoStr) : null;
  },
  setAuthorization: (value: string) => {
    if (persistCredentials) {
      browserStorage.setItem(RagflowStorageKey.Authorization, value);
    }
  },
  setToken: (value: string) => {
    if (persistCredentials) {
      browserStorage.setItem(RagflowStorageKey.Token, value);
    }
  },
  setUserInfo: (value: string | Record<string, unknown>) => {
    if (!persistCredentials) {
      return;
    }
    const valueStr = typeof value !== 'string' ? JSON.stringify(value) : value;
    browserStorage.setItem(RagflowStorageKey.UserInfo, valueStr);
  },
  setCredentials: ({ authorization, token, userInfo }: CredentialSet) => {
    if (!persistCredentials) {
      return;
    }
    const userInfoValue =
      typeof userInfo === 'string' ? userInfo : JSON.stringify(userInfo);
    browserStorage.setItem(RagflowStorageKey.Authorization, authorization);
    browserStorage.setItem(RagflowStorageKey.Token, token);
    browserStorage.setItem(RagflowStorageKey.UserInfo, userInfoValue);
  },
  removeAuthorization: () => {
    browserStorage.removeItem(RagflowStorageKey.Authorization);
  },
  removeAll: () => {
    CredentialKeySet.forEach((x) => {
      browserStorage.removeItem(x);
    });
  },
  setLanguage: (lng: string) => {
    browserStorage.setItem('lng', lng);
  },
  getLanguage: (): string => {
    return browserStorage.getItem('lng') as string;
  },
  setThinkingLevel: (level: string) => {
    browserStorage.setItem(RagflowStorageKey.ThinkingLevel, level);
  },
  getThinkingLevel: (): string => {
    return browserStorage.getItem(RagflowStorageKey.ThinkingLevel) || '1';
  },
});

const storage = createAuthorizationStorage(
  localStorage,
  !RuntimeConfig.embeddedAuth,
);

type AuthorizationSource = {
  embeddedAuth: boolean;
  searchAuthorization: string | null | undefined;
  storedAuthorization: string | null | undefined;
};

export const resolveAuthorization = ({
  embeddedAuth,
  searchAuthorization,
  storedAuthorization,
}: AuthorizationSource): string => {
  if (embeddedAuth) {
    return 'Bearer ragflow-embedded-proxy';
  }

  return searchAuthorization
    ? `Bearer ${searchAuthorization}`
    : storedAuthorization || '';
};

export const getAuthorization = () => {
  return resolveAuthorization({
    embeddedAuth: RuntimeConfig.embeddedAuth,
    searchAuthorization: getSearchValue('auth'),
    storedAuthorization: storage.getAuthorization(),
  });
};

export default storage;

type LoginRedirectSource = {
  embeddedAuth: boolean;
  basePath: string;
  origin: string;
};

export const resolveLoginRedirect = ({
  embeddedAuth,
  basePath,
  origin,
}: LoginRedirectSource): string | null => {
  if (embeddedAuth) {
    return null;
  }

  return new URL(`${basePath}login`, `${origin}/`).toString();
};

export function redirectToLogin() {
  const loginUrl = resolveLoginRedirect({
    embeddedAuth: RuntimeConfig.embeddedAuth,
    basePath: RuntimeConfig.basePath,
    origin: location.origin,
  });
  if (loginUrl) {
    window.location.href = loginUrl;
  }
}
