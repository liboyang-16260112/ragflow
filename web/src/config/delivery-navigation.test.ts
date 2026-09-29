import { filterDeliveryNavigation, getDeliveryReturnPath } from './delivery-navigation';

describe('filterDeliveryNavigation', () => {
  const items = [
    { path: '/', label: 'home' },
    { path: '/datasets', label: 'datasets' },
    { path: '/chats', label: 'chats' },
    { path: '/searches', label: 'searches' },
    { path: '/agents', label: 'agents' },
    { path: '/memories', label: 'memories' },
    { path: '/files', label: 'files' },
  ];

  it('hides chat, search, agent and memory navigation in embedded delivery mode', () => {
    expect(filterDeliveryNavigation(items, true).map((item) => item.path)).toEqual([
      '/',
      '/datasets',
      '/files',
    ]);
  });

  it('keeps the complete navigation outside embedded delivery mode', () => {
    expect(filterDeliveryNavigation(items, false)).toEqual(items);
  });
});


describe('getDeliveryReturnPath', () => {
  it('returns the QKQ knowledge workspace only in embedded delivery mode', () => {
    expect(getDeliveryReturnPath(true)).toBe('/#/workspace/knowledge');
    expect(getDeliveryReturnPath(false)).toBeNull();
  });
});
