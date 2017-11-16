# Slack alert action for Splunk

This app adds a new custom alert action to your Splunk instance which allows you
to send a message to a Slack channel.

## Dev Setup

This project uses the [Yarn](https://yarnpkg.com/) package manager. Once you have Yarn, use the following command to
install the dependencies:

```
$ yarn install
```

## Build & Package

In order to build the app run

```sh
$ yarn build
```

If you want to link your built app to a local Splunk instance, run

```sh
$ yarn symlink
```

Note: you'll have to have your `$SPLUNK_HOME` enviroment variable set correctly.

To build a package you can upload to [Splunkbase](http://splunkbase.com/), run the following command:

```sh
$ yarn package
```

This will create a `*.spl` file in the `dist/` directory.