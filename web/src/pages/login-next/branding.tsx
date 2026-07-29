import React from 'react';
import { useTranslation } from 'react-i18next';

void React;

export default function LoginBranding() {
  const { t } = useTranslation('translation', { keyPrefix: 'login' });

  return (
    <div className="z-20 absolute top-3 flex w-full flex-col items-center text-text-primary">
      <div className="mb-4 flex w-full items-center px-4 pt-10 sm:px-10">
        <div className="mr-3 flex size-12 items-center justify-center rounded-lg p-2">
          <img
            src="/fmoss-logo.png"
            alt="FMoss-RAG brand logo"
            className="size-8 mr-[12] cursor-pointer"
          />
        </div>
        <div className="text-xl font-bold self-center">FMoss-RAG</div>
      </div>
      <div className="w-full max-w-[960px] px-4 text-center sm:px-6">
        <h1 className="break-words text-[32px] font-medium leading-tight sm:text-[36px]">
          {t('heroTitle')}
        </h1>
        <p className="mt-2 break-words text-base leading-7 text-text-secondary sm:text-lg">
          {t('heroSubtitle')}
        </p>
      </div>
    </div>
  );
}
