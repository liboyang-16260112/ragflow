import fs from 'node:fs';
import path from 'node:path';

describe('embedded delivery navigation', () => {
  it('keeps return-to-knowledge navigation out of the centered RAGFlow navbar', () => {
    const source = fs.readFileSync(
      path.resolve(__dirname, 'global-navbar.tsx'),
      'utf8',
    );

    expect(source).not.toContain('返回知识问答');
    expect(source).not.toContain('getDeliveryReturnPath');
  });
});
