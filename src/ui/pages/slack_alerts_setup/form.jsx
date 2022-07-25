import Button from '@splunk/react-ui/Button';
import Code from '@splunk/react-ui/Code';
import CollapsiblePanel from '@splunk/react-ui/CollapsiblePanel';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Heading from '@splunk/react-ui/Heading';
import Link from '@splunk/react-ui/Link';
import Paragraph from '@splunk/react-ui/Paragraph';
import TabLayout from '@splunk/react-ui/TabLayout';
import Text from '@splunk/react-ui/Text';
import React, { useCallback } from 'react';
import { useSlackConfig, redirectToAlertListingPage } from './config';
import { openSlackMessagePreview } from './preview';
import { ButtonGroup, FormWrapper } from './styles';

export function SetupForm() {
    const [{ loading, error, data, isDirty }, update, save] = useSlackConfig();

    const updateOauthToken = useCallback((e, { value }) => update({ ...data, slack_app_oauth_token: value }));
    const updateUrl = useCallback((e, { value }) => update({ ...data, webhook_url: value }));
    const updateUser = useCallback((e, { value }) => update({ ...data, from_user: value }));
    const updateUserIcon = useCallback((e, { value }) => update({ ...data, from_user_icon: value }));

    const slackAppOauthToken = loading ? '' : data.slack_app_oauth_token;
    const webhookUrl = loading ? '' : data.webhook_url;
    const fromUserName = loading ? '' : data.from_user;
    const fromUserIcon = loading ? '' : data.from_user_icon;

    const oauth_app_manifest = `
display_information:
  name: Splunk Alerts
features:
  bot_user:
    display_name: Splunk
    always_online: false
oauth_config:
  scopes:
    bot:
      - chat:write
      - chat:write.public
      - chat:write.customize
settings:
  org_deploy_enabled: false
  socket_mode_enabled: false
  token_rotation_enabled: false`.trim();

    return (
        <>

            <TabLayout defaultActivePanelId="oauth">
                <TabLayout.Panel label="Slack App OAuth Token (preferred)" panelId="oauth" style={{ margin: 20 }}>
                    <Paragraph>
                        The Slack App OAuth token is the preferred method for using the Slack alert action.
                        The webhook url method (in the second tab) is deprecated and may be removed in a future release
                        of Slack.
                    </Paragraph>
                    <Heading level={3}>Slack App OAuth Token</Heading>
                    <Paragraph>
                        This alert action uses{' '}
                        <Link to="https://api.slack.com/apps" openInNewContext>
                            custom Slack Apps
                        </Link>{' '}
                        to post messages from Splunk into Slack channels. You can set a default Slack App OAuth
                        token here, which will be used for all alerts by default. Each alert can override and
                        use a different Slack App OAuth Token that has different permissions or can send to a
                        different Slack workspace.
                    </Paragraph>
                    <Paragraph>
                        Once you have the Slack App created, you <b>must</b> give the app permission to the{' '}
                        <code>chat:write</code>, <code>chat:write.public</code>, and <code>chat:write.customize</code>{' '}
                        OAuth scopes in your Slack workspace. You can grant these permissions in the "OAuth &amp;
                        Permissions" tab at the link above.
                    </Paragraph>
                    <Paragraph>
                        These scopes allow your app to write messages to every public channel and user in
                        your workspace. The app will also be able to write to any private channel, but it
                        will need to be explicitly granted access to each private channel.
                    </Paragraph>
                    <CollapsiblePanel title="Setting OAuth scopes using an app manifest">
                        <Paragraph style={{ margin: 20 }}>
                            Slack also lets you set OAuth scopes using the "App Manifest" tab. The code below
                            can be pasted into the App Manifest YAML input box to set all of the permissions above.
                        </Paragraph>
                        <Code  style={{ margin: 20 }} value={oauth_app_manifest} />
                    </CollapsiblePanel>
                    <FormWrapper>
                        <ControlGroup
                            label="Slack App OAuth Token"
                            help={
                                <Link to="https://api.slack.com/apps" openInNewContext>
                                    Configure Slack App OAuth token
                                </Link>
                            }
                        >
                            <Text
                                value={slackAppOauthToken}
                                onChange={updateOauthToken}
                                disabled={loading}
                                placeholder="xoxb-111111111111-2222222222222-abcdefghijklmnopqrstuvwx"
                            />
                        </ControlGroup>
                    </FormWrapper>
                </TabLayout.Panel>
                <TabLayout.Panel label="Slack Incoming Webhook (deprecated)" panelId="webhook" style={{ margin: 20 }}>
                    <Paragraph>
                        Slack has deprecated the "Incoming Webhooks" feature in favor of using{' '}
                        <Link to="https://api.slack.com/apps" openInNewContext>
                            Slack Apps
                        </Link>.{' '}
                        Slack may remove the incoming webhook feature in a future update. If you provide both a
                        "Slack App OAuth Token" and an "Incoming Webhook", then the "Slack App OAuth Token" will
                        take precedence. You can still override the OAuth token by using the "webhook_url_override"
                        parameter on an individual alert.
                    </Paragraph>
                    <Heading level={3}>Slack Incoming Webhook</Heading>
                    <Paragraph>
                        This alert action uses Slack's{' '}
                        <Link to="https://slack.com/apps/A0F7XDUAZ-incoming-webhooks" openInNewContext>
                            Incoming Webhooks
                        </Link>{' '}
                        to post messages from Splunk into Slack channels. You can set a default webhook URL here,
                        which will be used for all alerts by default. Each alert can override and use a different
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
                    </FormWrapper>
                </TabLayout.Panel>
            </TabLayout>

            <div style={{ margin: 20 }}>
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
            </div>
        </>
    );
}
