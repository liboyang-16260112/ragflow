import { RuntimeConfig } from '@/config/runtime';
import { LanguageAbbreviation } from '@/constants/common';
import storage from '@/utils/authorization-util';
import dayjs from 'dayjs';
import i18n from 'i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import { upperFirst } from 'lodash';
import { initReactI18next } from 'react-i18next';
import translation_en from './en';

//The language is based on the .ng file stored in the client's local storage.
// The language stored in the database is for agent template resources, as these resources reside on the server.
// When a user logs in from a different machine, the login page language is the language configured by VITE_DEFAULT_LANGUAGE_CODE.

const languageImports: Record<string, () => Promise<{ default: any }>> = {
  [LanguageAbbreviation.En]: () => import('./en'),
  [LanguageAbbreviation.Zh]: () => import('./zh'),
  [LanguageAbbreviation.ZhTraditional]: () => import('./zh-traditional'),
  [LanguageAbbreviation.Id]: () => import('./id'),
  [LanguageAbbreviation.Ja]: () => import('./ja'),
  [LanguageAbbreviation.Es]: () => import('./es'),
  [LanguageAbbreviation.Vi]: () => import('./vi'),
  [LanguageAbbreviation.Ru]: () => import('./ru'),
  [LanguageAbbreviation.PtBr]: () => import('./pt-br'),
  [LanguageAbbreviation.De]: () => import('./de'),
  [LanguageAbbreviation.Fr]: () => import('./fr'),
  [LanguageAbbreviation.It]: () => import('./it'),
  [LanguageAbbreviation.Bg]: () => import('./bg'),
  [LanguageAbbreviation.Ar]: () => import('./ar'),
  [LanguageAbbreviation.Tr]: () => import('./tr'),
  [LanguageAbbreviation.Ko]: () => import('./ko'),
};

const supportedLanguageCodes: Intl.UnicodeBCP47LocaleIdentifier[] =
  Object.keys(languageImports);

export const supportedLanguages = supportedLanguageCodes.map((code) => {
  const locale = new Intl.Locale(code);

  return {
    code,
    locale,
    displayName: upperFirst(
      new Intl.DisplayNames(locale, { type: 'language' }).of(code)!,
    ),
  };
});

const languageAliases: Record<string, string> = {
  zh: LanguageAbbreviation.Zh,
  'zh-cn': LanguageAbbreviation.Zh,
  'zh-hans': LanguageAbbreviation.Zh,
  'zh-tw': LanguageAbbreviation.ZhTraditional,
  'zh-hant': LanguageAbbreviation.ZhTraditional,
};

export const normalizeLanguageCode = (language?: string | null): string => {
  const value = language?.trim();
  if (!value) return LanguageAbbreviation.Zh;

  return languageAliases[value.replace('_', '-').toLowerCase()] || value;
};

export const DEFAULT_LANGUAGE_CODE = normalizeLanguageCode(
  import.meta.env?.VITE_DEFAULT_LANGUAGE_CODE || LanguageAbbreviation.Zh,
);

export const resolveInitialLanguage = ({
  embeddedAuth,
  savedLanguage,
  defaultLanguage,
}: {
  embeddedAuth: boolean;
  savedLanguage?: string | null;
  defaultLanguage: string;
}): string =>
  normalizeLanguageCode(
    embeddedAuth ? defaultLanguage : savedLanguage || defaultLanguage,
  );

export const resolveRequestedLanguage = ({
  embeddedAuth,
  requestedLanguage,
  defaultLanguage,
}: {
  embeddedAuth: boolean;
  requestedLanguage: string;
  defaultLanguage: string;
}): string =>
  normalizeLanguageCode(embeddedAuth ? defaultLanguage : requestedLanguage);

const resources = {
  [LanguageAbbreviation.En]: translation_en,
};

const updateDocumentLocale = (lng: string) => {
  document.documentElement.lang = lng;
  document.documentElement.dir = 'ltr';
  dayjs.locale(
    lng === LanguageAbbreviation.Zh
      ? 'zh-cn'
      : lng === LanguageAbbreviation.ZhTraditional
        ? 'zh-tw'
        : lng,
  );
};

i18n
  .use(initReactI18next)
  .use(LanguageDetector)
  .init({
    detection: {
      lookupLocalStorage: 'lng',
      order: ['localStorage'],
      caches: [],
    },
    supportedLngs: supportedLanguageCodes,
    resources,
    fallbackLng: LanguageAbbreviation.En,
    interpolation: {
      escapeValue: false,
    },
  });

export const loadLanguageAsync = async (lng: string): Promise<void> => {
  const normalizedLng = normalizeLanguageCode(lng);

  if (i18n.hasResourceBundle(normalizedLng, 'translation')) {
    return;
  }

  const importFn = languageImports[normalizedLng];
  if (!importFn) {
    console.warn(`Language ${lng} is not supported for lazy loading`);
    return;
  }

  try {
    const module = await importFn();
    const translationData = module.default?.translation || module.default;
    i18n.addResourceBundle(normalizedLng, 'translation', translationData);
  } catch (error) {
    console.error(`Failed to load language ${lng}:`, error);
  }
};

export const changeLanguageAsync = async (
  lng: string,
  options: { persist?: boolean } = {},
): Promise<void> => {
  const { persist = true } = options;
  const normalizedLng = resolveRequestedLanguage({
    embeddedAuth: RuntimeConfig.embeddedAuth,
    requestedLanguage: lng,
    defaultLanguage: DEFAULT_LANGUAGE_CODE,
  });

  if (
    normalizedLng !== LanguageAbbreviation.En &&
    !i18n.hasResourceBundle(normalizedLng, 'translation')
  ) {
    await loadLanguageAsync(normalizedLng);
  }

  if (persist) {
    storage.setLanguage(normalizedLng);
  }

  updateDocumentLocale(normalizedLng);

  await i18n.changeLanguage(normalizedLng);
};

export const initLanguage = async (): Promise<void> => {
  const currentLng = resolveInitialLanguage({
    embeddedAuth: RuntimeConfig.embeddedAuth,
    savedLanguage: storage.getLanguage(),
    defaultLanguage: DEFAULT_LANGUAGE_CODE,
  });

  await changeLanguageAsync(currentLng);
};

export default i18n;
