import { useState, useEffect, useCallback } from 'react';
import { makeUrl } from './utils';
import Toaster, { makeCreateToast } from '@splunk/react-toast-notifications/Toaster';

const createToast = makeCreateToast(Toaster);

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

export function loadConfig() {
    return fetch(
        makeUrl('/splunkd/__raw/servicesNS/-/-/alerts/alert_actions/slack?output_mode=json&_=' + Date.now())
    )
        .then((res) => {
            if (!res.ok) {
                throw new Error(`Failed to fetch config: HTTP status ${res.status}`);
            }
            return res.json();
        })
        .then((data) => {
            const d = data.entry[0].content;
            return {
                webhook_url: d['param.webhook_url'],
                from_user: d['param.from_user'],
                from_user_icon: d['param.from_user_icon'],
            };
        });
}

export function updateConfig(data) {
    return fetch(
        makeUrl(`/splunkd/__raw/servicesNS/-/slack_alerts/alerts/alert_actions/slack?output_mode=json`),
        {
            method: 'POST',
            body: [
                `param.webhook_url=${encodeURIComponent(data.webhook_url)}`,
                `param.from_user=${encodeURIComponent(data.from_user)}`,
                `param.from_user_icon=${encodeURIComponent(data.from_user_icon)}`,
            ].join('&'),
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest',
                'X-Splunk-Form-Key': getFormKey(),
            },
        }
    ).then((res) => {
        if (!res.ok) {
            throw new Error(`Failed to save: HTTP status ${res.status}`);
        }
    });
}

const eq = (a, b) => {
    const ka = Object.keys(a);
    const kb = Object.keys(b);
    return ka.length === kb.length && ka.every((k) => k in b && a[k] === b[k]);
};

export function useSlackConfig() {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [savedData, setSavedData] = useState({});
    const [data, setData] = useState({});

    useEffect(() => {
        loadConfig().then(
            (cfg) => {
                setSavedData(cfg);
                setData(cfg);
                setLoading(false);
            },
            (e) => {
                setError(`Error: ${e.message}`);
                setLoading(false);
            }
        );
    }, [setLoading, setError]);

    const update = useCallback(
        (data) => {
            setData(data);
        },
        [setData]
    );

    const save = useCallback(() => {
        if (!eq(savedData, data)) {
            updateConfig(data).then(
                () => {
                    setSavedData(data);
                    createToast({
                        message: 'Successfully updated Slack alert action',
                        type: 'success',
                    });
                },
                (e) => {
                    setError(`Error: ${e.message}`);
                    createToast({
                        message: `Failed to save changes: ${e.message}`,
                        type: 'error',
                        autoDismiss: false,
                    });
                }
            );
        }
    }, [data, savedData, setSavedData, setError]);

    return [{ loading, error, data, isDirty: !eq(savedData, data) }, update, save];
}

export function redirectToAlertListingPage() {
    window.location = makeUrl('/manager/slack_alerts/alert_actions');
}
