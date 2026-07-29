import { LanguageAbbreviation } from '@/constants/common';
import i18n, { changeLanguageAsync } from '@/locales/config';
import translation_de from '@/locales/de';
import translation_zh from '@/locales/zh';
import { cleanup, render, screen } from '@testing-library/react';
import React from 'react';
import LoginBranding from './branding';

void React;

describe('LoginBranding', () => {
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

  afterEach(() => {
    cleanup();
    localStorage.clear();
  });

  it('renders the FMoss-RAG identity and Chinese hero copy', async () => {
    await changeLanguageAsync(LanguageAbbreviation.Zh);

    render(<LoginBranding />);

    const logo = screen.getByRole('img', {
      name: 'FMoss-RAG brand logo',
    });
    expect(logo).toHaveAttribute('src', '/fmoss-logo.png');
    expect(logo).toHaveAttribute(
      'class',
      'size-8 mr-[12] cursor-pointer',
    );
    expect(screen.getByText('FMoss-RAG')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', {
        level: 1,
        name: 'FMoss 智能知识增强引擎',
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText('打通非结构化数据与 LLM 之间的精准检索链路'),
    ).toBeInTheDocument();
  });

  it('renders English hero copy through fallback for another locale', async () => {
    await changeLanguageAsync(LanguageAbbreviation.De);

    render(<LoginBranding />);

    expect(
      screen.getByRole('heading', {
        level: 1,
        name: 'FMoss intelligent knowledge augmentation engine',
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        'Connecting unstructured data to precise retrieval for LLMs',
      ),
    ).toBeInTheDocument();
  });
});
