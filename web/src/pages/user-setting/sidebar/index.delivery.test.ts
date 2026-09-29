import fs from 'node:fs';
import path from 'node:path';

describe('embedded delivery user-setting sidebar', () => {
  it('omits the standalone RAGFlow logout action while retaining account settings', () => {
    const source = fs.readFileSync(path.resolve(__dirname, 'index.tsx'), 'utf8');

    expect(source).not.toContain('useLogout');
    expect(source).not.toContain('LucideLogOut');
    expect(source).not.toContain("t('setting.logout')");
    expect(source).toContain('<ThemeSwitch />');
    expect(source).toContain('userInfo?.email');
  });
});
