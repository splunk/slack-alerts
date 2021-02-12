import Button from '@splunk/react-ui/Button';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Heading from '@splunk/react-ui/Heading';
import Link from '@splunk/react-ui/Link';
import Paragraph from '@splunk/react-ui/Paragraph';
import Text from '@splunk/react-ui/Text';
import React, { useCallback } from 'react';
import { useSlackConfig, redirectToAlertListingPage } from './config';
import { openSlackMessagePreview } from './preview';
import { ButtonGroup, FormWrapper } from './styles';

export function SetupForm() {
    const [{ loading, error, data, isDirty }, update, save] = useSlackConfig();

    const updateUrl = useCallback((e, { value }) => update({ ...data, webhook_url: value }));
    const updateUser = useCallback((e, { value }) => update({ ...data, from_user: value }));
    const updateUserIcon = useCallback((e, { value }) => update({ ...data, from_user_icon: value }));
    const updateProxy = useCallback((e, { value }) => update({ ...data, http_proxy: value }));

    const webhookUrl = loading ? '' : data.webhook_url;
    const fromUserName = loading ? '' : data.from_user;
    const fromUserIcon = loading ? '' : data.from_user_icon;
    const httpProxy = loading ? '' : data.http_proxy;

    return (
        <>
            <Heading level={3}>Slack Incoming Webhook</Heading>
            <Paragraph>
                This alert action uses Slack's{' '}
                <Link to="https://slack.com/apps/A0F7XDUAZ-incoming-webhooks" openInNewContext>
                    Incoming Webhooks
                </Link>{' '}
                to post messages from Splunk into Slack channels. You can set a default webhook URL here,
                which will be used for all alerts be default. Each alert can override and use a different
                webhook URL that has different permissions or can send to a different Slack workspace.
            </Paragraph>
            <FormWrapper>
                <ControlGroup
                    label="Webhook URL"
                    help={
                        <Link to="https://slack.com/apps/A0F7XDUAZ-incoming-webhooks" openInNewContext>
                            Configure Slack incoming webhook
                        </Link>
                    }
                >
                    <Text
                        value={webhookUrl}
                        onChange={updateUrl}
                        disabled={loading}
                        placeholder="https://hooks.slack.com/services/XXXXX/YYYY/ZZZZZ"
                    />
                </ControlGroup>
                <ControlGroup label="Proxy" help="Configure proxy ( optional )">
                    <Text
                        value={httpProxy}
                        onChange={updateProxy}
                        disabled={loading}
                        placeholder="http://yourproxy:port"
                    />
                </ControlGroup>
            </FormWrapper>
            <Heading level={3}>Message Appearance</Heading>
            <Paragraph>
                The following settings will influence how messages will show up in Slack.{' '}
                <Link onClick={() => openSlackMessagePreview(data)} openInNewContext>
                    Show Preview
                </Link>
                .
            </Paragraph>
            <FormWrapper>
                <ControlGroup
                    label="Sender Name"
                    help="This name will appear in slack as the user sending the message."
                >
                    <Text value={fromUserName} onChange={updateUser} disabled={loading} />
                </ControlGroup>
                <ControlGroup
                    label="Sender Icon"
                    help="The avatar/icon shown by the sender of the slack message. This URL needs to be accessible from the internet."
                >
                    <Text value={fromUserIcon} onChange={updateUserIcon} disabled={loading} />
                </ControlGroup>
            </FormWrapper>
            <ButtonGroup>
                <div>
                    <Button label="Cancel" appearance="secondary" onClick={redirectToAlertListingPage} />
                </div>
                <div>
                    <Button label="Save" appearance="primary" disabled={loading || !isDirty} onClick={save} />
                </div>
            </ButtonGroup>
        </>
    );
}
