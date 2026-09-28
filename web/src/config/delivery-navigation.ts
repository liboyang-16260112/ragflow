const hiddenEmbeddedPaths = new Set([
  '/chats',
  '/searches',
  '/agents',
  '/memories',
]);

export const filterDeliveryNavigation = <T extends { path: string }>(
  items: T[],
  embeddedAuth: boolean,
): T[] =>
  embeddedAuth
    ? items.filter((item) => !hiddenEmbeddedPaths.has(item.path))
    : items;

export const getDeliveryReturnPath = (embeddedAuth: boolean): string | null =>
  embeddedAuth ? '/#/workspace/knowledge' : null;
