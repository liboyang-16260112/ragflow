import fs from 'node:fs';
import path from 'node:path';

describe('embedded delivery header', () => {
  it('uses the upper-left size-10 logo to return to the top-level QKQ knowledge workspace', () => {
    const source = fs.readFileSync(path.resolve(__dirname, 'header.tsx'), 'utf8');

    expect(source).toContain('getDeliveryReturnPath');
    expect(source).toContain('href={deliveryReturnPath}');
    expect(source).toContain('target="_top"');
    expect(source).toContain('aria-label="返回知识问答"');
    expect(source).toContain('className="flex size-10 shrink-0 items-center justify-center"');
  });
});
