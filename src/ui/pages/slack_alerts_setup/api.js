import { getFormKey, makeUrl } from './utils';

export function loadAlertActionConfig() {
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
                slack_app_oauth_token: d['param.slack_app_oauth_token'],
                webhook_url: d['param.webhook_url'],
                from_user: d['param.from_user'],
                from_user_icon: d['param.from_user_icon'],
                http_proxy: d['param.http_proxy'],
            };
        });
}

export function updateAlertActionConfig(data) {
    return fetch(
        makeUrl(`/splunkd/__raw/servicesNS/-/slack_alerts/alerts/alert_actions/slack?output_mode=json`),
        {
            method: 'POST',
            body: [
                `param.slack_app_oauth_token=${encodeURIComponent(data.slack_app_oauth_token)}`,
                `param.webhook_url=${encodeURIComponent(data.webhook_url)}`,
                `param.from_user=${encodeURIComponent(data.from_user)}`,
                `param.from_user_icon=${encodeURIComponent(data.from_user_icon)}`,
                `param.http_proxy=${encodeURIComponent(data.http_proxy)}`,
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
