export function makeUrl(path) {
    const { LOCALE, MRSPARKLE_ROOT_PATH } = window.$C;
    return `${MRSPARKLE_ROOT_PATH || ''}/${LOCALE}${path}`;
}
