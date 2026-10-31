# COT positioning: auto-updating pages

Two self-contained HTML pages ranking speculative net positions in 30 futures
contracts (net % of open interest, 1y/3y z-scores, weekly movers, 5-year
histories), rebuilt from the CFTC Public Reporting API after each weekly
release:

- `noncomm` : Legacy report, non-commercial traders
- `spec`    : Traders in Financial Futures leveraged funds (financials) +
              Disaggregated managed money (gold, copper, WTI)

A Claude artifact cannot call the CFTC API itself (the artifact sandbox blocks
outside requests), so the data pull runs here, on GitHub Actions, and a weekly
scheduled Claude task republishes the two artifacts from the built pages.

## Files

```
universe.json            30 contracts: CFTC code, label, asset class, which "spec" dataset
fetch_cot.py             Socrata API -> data/noncomm.json, data/spec.json  (stdlib only)
build_pages.py           template + data -> artifact/*.html (for Claude) and site/*.html (full documents)
cot_live.html            page template: all analysis (net, % OI, rolling z, ranks) runs in the browser
.github/workflows/cot.yml  schedule: Fri 21:45 and 23:30 UTC, Mon/Tue 22:00 UTC (holiday releases), manual run
                         (delivered as workflow-cot.yml: move it to .github/workflows/cot.yml in the repo)
data/                    weekly rows [date, code, open_interest, long, short, spread] from 2018
artifact/                page bodies published as Claude artifacts
site/                    same pages as complete HTML documents (GitHub Pages, local viewing)
```

## Set up (once)

1. Put these files at the root of a GitHub repository (public is fine; the data
   is public), move `workflow-cot.yml` to `.github/workflows/cot.yml`, and push.
2. Actions tab -> "CFTC COT positioning data" -> Run workflow. The first run
   downloads about 8 years of weekly data (a few seconds) and commits
   `data/`, `artifact/` and `site/`.
3. The weekly Claude scheduled task reads
   `https://raw.githubusercontent.com/<owner>/<repo>/main/artifact/noncomm.html`
   and `.../artifact/spec.html` and republishes the two artifacts.

If the files live in a subfolder instead of the repo root, add
`defaults: run: working-directory: <folder>` to the workflow job and prefix the
`git add` paths.

## Method

Identical to the Quarto report in the "COT data" project: net = long − short
(spreads excluded); % OI = net / total open interest; z-scores over trailing
calendar windows of 364 and 1,092 days including the current week, shown once
80% of the window exists; rankings from most net long to most net short. The
page recomputes everything from the embedded weekly rows, so the as-of week and
the z-score basis (net contracts or net % OI) can be switched in the page.
Checked against the R implementation: identical to display precision.

## Local use

`python fetch_cot.py && python build_pages.py` then open `site/noncomm.html`.
Python 3.9+; no packages beyond the standard library.
