export function makeUrl(path) {
    const { LOCALE, MRSPARKLE_ROOT_PATH } = window.$C;
    return `${MRSPARKLE_ROOT_PATH || ''}/${LOCALE}${path}`;
}

function getFormKey() {
    const prefix = `splunkweb_csrf_token_${window.$C.MRSPARKLE_PORT_NUMBER}=`;
    if (document.cookie) {
        for (const chunk of document.cookie.split(';')) {
            const cookie = String(chunk).trim();
            if (cookie.startsWith(prefix)) {
                return decodeURIComponent(cookie.slice(prefix.length));
            }
        }
    }
}

const eq = (a, b) => {
    const ka = Object.keys(a);
    const kb = Object.keys(b);
    return ka.length === kb.length && ka.every((k) => k in b && a[k] === b[k]);
};
