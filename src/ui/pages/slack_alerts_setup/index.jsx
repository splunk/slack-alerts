import layout from '@splunk/react-page';
import Heading from '@splunk/react-ui/Heading';
import React from 'react';
import { SetupForm } from './form';
import { BodyWrapper, Dialog, DialogWrapper, TitleWrapper } from './styles';
import ToastMessages from '@splunk/react-toast-notifications/ToastMessages';

function SlackSetupPage() {
    return (
        <BodyWrapper>
            <TitleWrapper>
                <Heading level={1}>Slack Alerts Setup</Heading>
            </TitleWrapper>
            <DialogWrapper>
                <Dialog>
                    <SetupForm />
                </Dialog>
            </DialogWrapper>
            <ToastMessages />
        </BodyWrapper>
    );
}

layout(<SlackSetupPage />, { pageTitle: 'Slack Alert setup', hideAppBar: true });
