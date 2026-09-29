import { LanguageAbbreviation } from '@/constants/common';
import storage from '@/utils/authorization-util';
import translation_de from './de';
import i18n, {
  changeLanguageAsync,
  DEFAULT_LANGUAGE_CODE,
  initLanguage,
  normalizeLanguageCode,
  resolveInitialLanguage,
  resolveRequestedLanguage,
} from './config';
import translation_zh from './zh';

describe('language initialization', () => {
  beforeAll(() => {
    i18n.addResourceBundle(
      LanguageAbbreviation.Zh,
      'translation',
      translation_zh.translation,
      true,
      true,
    );
    i18n.addResourceBundle(
      LanguageAbbreviation.De,
      'translation',
      translation_de.translation,
      true,
      true,
    );
  });

  beforeEach(async () => {
    localStorage.clear();
    await changeLanguageAsync(LanguageAbbreviation.En);
    localStorage.clear();
  });

  it('falls back to Simplified Chinese when the environment value is absent', () => {
    expect(DEFAULT_LANGUAGE_CODE).toBe(LanguageAbbreviation.Zh);
  });

  it('initializes a browser without a saved preference in Simplified Chinese', async () => {
    await initLanguage();

    expect(i18n.language).toBe(LanguageAbbreviation.Zh);
    expect(document.documentElement.lang).toBe(LanguageAbbreviation.Zh);
    expect(storage.getLanguage()).toBe(LanguageAbbreviation.Zh);
  });

  it('forces the configured Simplified Chinese default in embedded delivery mode', () => {
    expect(
      resolveInitialLanguage({
        embeddedAuth: true,
        savedLanguage: LanguageAbbreviation.En,
        defaultLanguage: LanguageAbbreviation.Zh,
      }),
    ).toBe(LanguageAbbreviation.Zh);
  });

  it('normalizes the production zh alias to the RAGFlow Simplified Chinese locale', () => {
    expect(normalizeLanguageCode('zh')).toBe(LanguageAbbreviation.Zh);
    expect(
      resolveInitialLanguage({
        embeddedAuth: true,
        savedLanguage: LanguageAbbreviation.En,
        defaultLanguage: 'zh',
      }),
    ).toBe(LanguageAbbreviation.Zh);
  });


  it('rejects attempts to switch an embedded delivery page back to English', () => {
    expect(
      resolveRequestedLanguage({
        embeddedAuth: true,
        requestedLanguage: LanguageAbbreviation.En,
        defaultLanguage: LanguageAbbreviation.Zh,
      }),
    ).toBe(LanguageAbbreviation.Zh);
  });

  it('prefers a saved English language selection outside embedded delivery mode', async () => {
    storage.setLanguage(LanguageAbbreviation.En);

    await initLanguage();

    expect(i18n.language).toBe(LanguageAbbreviation.En);
    expect(document.documentElement.lang).toBe(LanguageAbbreviation.En);
  });

  it('uses English fallback copy when the current locale omits new login keys', async () => {
    await changeLanguageAsync(LanguageAbbreviation.De);

    expect(i18n.t('login.heroTitle')).toBe(
      'FMoss intelligent knowledge augmentation engine',
    );
    expect(i18n.t('login.heroSubtitle')).toBe(
      'Connecting unstructured data to precise retrieval for LLMs',
    );
  });

  it('preserves the saved language when authentication state is cleared', () => {
    storage.setAuthorization('authorization');
    storage.setToken('token');
    storage.setLanguage(LanguageAbbreviation.En);

    storage.removeAll();

    expect(storage.getAuthorization()).toBeNull();
    expect(storage.getToken()).toBeNull();
    expect(storage.getLanguage()).toBe(LanguageAbbreviation.En);
  });
});
