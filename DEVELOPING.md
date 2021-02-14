## Dev Setup

Prerequisites:

-   Node.js 12
-   [Yarn](https://yarnpkg.com/) package manager
-   Python 2.x and or 3.x

### Bootstrap project - install dependencies

```
$ cd slack_alerts
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

Note: you'll have to have your `$SPLUNK_HOME` environment variable set correctly.

To build a package you can upload to [Splunkbase](http://splunkbase.com/), run the following command:

```sh
$ yarn package
```

This will create a `*.spl` file in the `dist/` directory.

## Code Style

This project uses [prettier](https://github.com/prettier/prettier) to ensure consistent code formatting. You may want to add a prettier plugin to your editor/ide for a smooth experience.

## Run Tests

To execute unit tests, run:

```sh-session
$ yarn test
```

(This requires a python environment to be set up)
