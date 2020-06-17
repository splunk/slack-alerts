import Toaster, { makeCreateToast } from '@splunk/react-toast-notifications/Toaster';
import { useCallback, useEffect, useState } from 'react';
import { loadAlertActionConfig, updateAlertActionConfig } from './api';
import { eq, makeUrl } from './utils';

const createToast = makeCreateToast(Toaster);

export function useSlackConfig() {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [savedData, setSavedData] = useState({});
    const [data, setData] = useState({});

    useEffect(() => {
        loadAlertActionConfig().then(
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
            updateAlertActionConfig(data).then(
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
