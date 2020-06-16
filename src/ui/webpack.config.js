const fs = require('fs');
const path = require('path');
const webpack = require('webpack');
const webpackMerge = require('webpack-merge');
const LiveReloadPlugin = require('webpack-livereload-plugin');
const baseConfig = require('@splunk/webpack-configs').default;

const DEBUG = process.env.NODE_ENV !== 'production';
const SRC_DIR = path.join(__dirname, 'pages');

const entries = fs
    .readdirSync(SRC_DIR)
    .filter(function (pageFile) {
        return !/^\./.test(pageFile);
    })
    .reduce(function (accum, page) {
        accum[page] = path.join(SRC_DIR, page);
        return accum;
    }, {});

module.exports = webpackMerge(baseConfig, {
    entry: entries,
    devtool: 'eval-source-map',
    optimization: {
        splitChunks: {
            name: 'common',
            chunks: 'all',
        },
    },
    output: {
        path: path.join(__dirname, '..', '..', 'stage', 'slack_alerts', 'appserver', 'static', 'pages'), // TODO use process.env.SLAP_STAGE_DIR
        filename: '[name].js',
        chunkFilename: '[name].js',
    },
    plugins: DEBUG
        ? [
              new LiveReloadPlugin({
                  appendScriptTag: true,
              }),
          ]
        : [],
});
