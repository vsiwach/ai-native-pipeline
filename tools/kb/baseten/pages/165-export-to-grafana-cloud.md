# Export to Grafana Cloud
Source: https://docs.baseten.co/observability/export-metrics/grafana

Export metrics from Baseten to Grafana Cloud

The Baseten + Grafana Cloud integration enables you to get real-time inference metrics within your existing Grafana setup.

## Video tutorial

See below for step-by-step details from the video.

<iframe title="YouTube video player" />

## Set up the integration

Open your Grafana Cloud account:

1. Navigate to "Home > Connections > Add new connection".
2. In the search bar, type `Metrics Endpoint` and select it.
3. Give your scrape job a name like `baseten_metrics_scrape`.
4. Set the scrape job URL to `https://app.baseten.co/metrics`.
5. Leave the scrape interval set to `Every minute`.
6. Select `Bearer` for authentication credentials.
7. In your Baseten account, generate a metrics-only workspace API key.
8. In Grafana, enter the Bearer Token as `Api-Key abcd.1234567890` where the latter value is replaced by your API key.
9. Use the "Test Connection" button to ensure everything is entered correctly.
10. Click "Save Scrape Job."
11. Click "Install."
12. In your integrations list, select your new export and go through the "Enable" flow shown on video.

Now, you can navigate to your Dashboards tab, where you'll see your data! Data can take a couple of minutes to arrive, and only new data is scraped, not historical metrics.

## Build a Grafana dashboard

Importing the data is a great first step, but you'll need a dashboard to properly visualize the incoming information.

We've prepared a basic dashboard to get you started, which you can import by:

1. Downloading `baseten_grafana_dashboard.json` from [this GitHub Gist](https://gist.github.com/philipkiely-baseten/9952e7592775ce1644944fb644ba2a9c).
2. Selecting "New > Import" from the dropdown in the top-right corner of the Dashboard page.
3. Dropping in the provided JSON file.

For visual reference in navigating the dashboard, please see the video above.
