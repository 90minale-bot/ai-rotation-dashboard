# initial stock project
STOCK ANALYTICS – DEFENSE SECTOR AI MODEL

===========================================

PROJECT OVERVIEW

This project is a local AI-powered stock analytics platform focused on
DEFENSE SECTOR stocks.

It combines:

Technical indicators

Defense-sector ETF context (ITA)

Relative strength features

Machine learning prediction

Workflow:

Select Stock → Download Data → Build Features →
Train Model → Launch Interactive Dashboard

Everything runs locally using Python + Streamlit.

CORE IDEA

Traditional models only look at one stock.

This project models:

STOCK behavior

DEFENSE SECTOR behavior (ITA ETF)

RELATIVE STRENGTH (Stock vs Sector)

This creates a sector-aware model similar to professional quant workflows.

PROJECT STRUCTURE

Stock-analytics/
│
├── main.py
│ Defense-sector model training
│
├── run_dashboard.bat
│ Auto launcher:
│ - asks for ticker
│ - trains model
│ - launches dashboard
│
├── Models/
│ <SYMBOL>_model.pkl
│ Saved model artifact
│
├── Dashboard/
│ dashboard.py
│ Streamlit display + prediction
│
└── README.txt

TECHNOLOGY STACK

Core:

Python

Streamlit

Pandas

NumPy

Plotly

Data:

Yahoo Finance via yahooquery

Machine Learning:

scikit-learn

Ridge Regression

StandardScaler

TimeSeriesSplit cross validation

Model persistence:

joblib

MODEL TARGET

The model predicts:

target_next_ret_1

Meaning:

NEXT-DAY RETURN (not raw price)

Dashboard converts this into:

Predicted Next Close =
Current Close * (1 + predicted return)

FEATURE CATEGORIES
1) STOCK FEATURES

Momentum:

stock_ret_1

stock_ret_5

stock_ret_10

Trend:

stock_gap_ma5

stock_gap_ma10

stock_gap_ma20

Volatility:

stock_vol_5

stock_vol_10

stock_vol_20

Optional (if available):

stock_hl_range

stock_vol_chg_1

stock_vol_z_20

2) DEFENSE SECTOR FEATURES (ITA ETF)

Sector proxy:

ITA = iShares U.S. Aerospace & Defense ETF

Variables:

ita_ret_1

ita_ret_5

ita_ret_10

ita_gap_ma20

ita_vol_10

3) RELATIVE STRENGTH (KEY UPGRADE)

These measure stock vs sector performance:

rel_ret_1

rel_ret_5

rel_ret_10

rel_gap_ma20

rel_vol_10

Example:

If stock +2% and ITA +0.5%:

rel_ret_1 = +1.5%

This captures sector leadership behavior.

MODEL ARTIFACT STRUCTURE

Models are saved as:

Models/<SYMBOL>_model.pkl

Artifact contents:

{
"model": sklearn pipeline,
"features": [feature list],
"target": "target_next_ret_1",
"meta": training info
}

This guarantees:

consistent training vs dashboard features

no feature mismatch errors

HOW TO RUN
OPTION 1 (RECOMMENDED)

Double-click:

run_dashboard.bat

Process:

Enter stock symbol

Train model

Launch Streamlit dashboard

Example:

Enter stock symbol: NOC

OPTION 2 (MANUAL)

Activate environment:

venv\Scripts\activate

Train model:

python main.py --symbol NOC

Launch dashboard:

streamlit run Dashboard\dashboard.py -- --symbol NOC

DASHBOARD FEATURES

Interactive price chart

Stock vs ITA sector chart

Moving averages

Volatility display

Model prediction section

Training metadata display

Prediction output:

Predicted next-day return

Implied next-day close price

DESIGN DECISIONS

Why predict return instead of price?

More stable statistical behavior

Removes long-term price drift

Easier to model

Why ITA?

Defense stocks often move together

Acts as a sector benchmark

Why relative strength?

Strong predictive signal

Identifies leaders vs laggards

KNOWN FIXES IMPLEMENTED

Timezone normalization (tz-aware vs tz-naive)

Streamlit symbol sticking (AAPL issue)

Model artifact loading (dict format)

Feature mismatch handling

BAT auto-symbol handling

CURRENT MODEL LEVEL

This project has moved from:

"Single stock technical analysis"

to:

"Sector-aware quant modeling"

FUTURE ROADMAP

Short term:

Add defense peer basket index (LMT, RTX, GD, LHX, NOC)

Model feature importance display

Prediction confidence score

Medium term:

Multi-stock scanner

Rank defense stocks by signal strength

Backtesting engine

Advanced:

Macro inputs (rates, oil, geopolitics)

News sentiment scoring

Regime detection (risk-on vs risk-off)

LONG TERM VISION

    Build a personal AI-powered quant workstation capable of:

    Monitoring sectors

    Identifying strong opportunities

    Combining technical + sector intelligence

    Supporting investment decision workflows


## Getting started

To make it easy for you to get started with GitLab, here's a list of recommended next steps.

Already a pro? Just edit this README.md and make it your own. Want to make it easy? [Use the template at the bottom](#editing-this-readme)!

## Add your files

* [Create](https://docs.gitlab.com/user/project/repository/web_editor/#create-a-file) or [upload](https://docs.gitlab.com/user/project/repository/web_editor/#upload-a-file) files
* [Add files using the command line](https://docs.gitlab.com/topics/git/add_files/#add-files-to-a-git-repository) or push an existing Git repository with the following command:

```
cd existing_repo
git remote add origin http://localhost/root/initial-stock-project.git
git branch -M main
git push -uf origin main
```

## Integrate with your tools

* [Set up project integrations](http://localhost/root/initial-stock-project/-/settings/integrations)

## Collaborate with your team

* [Invite team members and collaborators](https://docs.gitlab.com/user/project/members/)
* [Create a new merge request](https://docs.gitlab.com/user/project/merge_requests/creating_merge_requests/)
* [Automatically close issues from merge requests](https://docs.gitlab.com/user/project/issues/managing_issues/#closing-issues-automatically)
* [Enable merge request approvals](https://docs.gitlab.com/user/project/merge_requests/approvals/)
* [Set auto-merge](https://docs.gitlab.com/user/project/merge_requests/auto_merge/)

## Test and Deploy

Use the built-in continuous integration in GitLab.

* [Get started with GitLab CI/CD](https://docs.gitlab.com/ci/quick_start/)
* [Analyze your code for known vulnerabilities with Static Application Security Testing (SAST)](https://docs.gitlab.com/user/application_security/sast/)
* [Deploy to Kubernetes, Amazon EC2, or Amazon ECS using Auto Deploy](https://docs.gitlab.com/topics/autodevops/requirements/)
* [Use pull-based deployments for improved Kubernetes management](https://docs.gitlab.com/user/clusters/agent/)
* [Set up protected environments](https://docs.gitlab.com/ci/environments/protected_environments/)

***

# Editing this README

When you're ready to make this README your own, just edit this file and use the handy template below (or feel free to structure it however you want - this is just a starting point!). Thanks to [makeareadme.com](https://www.makeareadme.com/) for this template.

## Suggestions for a good README

Every project is different, so consider which of these sections apply to yours. The sections used in the template are suggestions for most open source projects. Also keep in mind that while a README can be too long and detailed, too long is better than too short. If you think your README is too long, consider utilizing another form of documentation rather than cutting out information.

## Name
Choose a self-explaining name for your project.

## Description
Let people know what your project can do specifically. Provide context and add a link to any reference visitors might be unfamiliar with. A list of Features or a Background subsection can also be added here. If there are alternatives to your project, this is a good place to list differentiating factors.

## Badges
On some READMEs, you may see small images that convey metadata, such as whether or not all the tests are passing for the project. You can use Shields to add some to your README. Many services also have instructions for adding a badge.

## Visuals
Depending on what you are making, it can be a good idea to include screenshots or even a video (you'll frequently see GIFs rather than actual videos). Tools like ttygif can help, but check out Asciinema for a more sophisticated method.

## Installation
Within a particular ecosystem, there may be a common way of installing things, such as using Yarn, NuGet, or Homebrew. However, consider the possibility that whoever is reading your README is a novice and would like more guidance. Listing specific steps helps remove ambiguity and gets people to using your project as quickly as possible. If it only runs in a specific context like a particular programming language version or operating system or has dependencies that have to be installed manually, also add a Requirements subsection.

## Usage
Use examples liberally, and show the expected output if you can. It's helpful to have inline the smallest example of usage that you can demonstrate, while providing links to more sophisticated examples if they are too long to reasonably include in the README.

## Support
Tell people where they can go to for help. It can be any combination of an issue tracker, a chat room, an email address, etc.

## Roadmap
If you have ideas for releases in the future, it is a good idea to list them in the README.

## Contributing
State if you are open to contributions and what your requirements are for accepting them.

For people who want to make changes to your project, it's helpful to have some documentation on how to get started. Perhaps there is a script that they should run or some environment variables that they need to set. Make these steps explicit. These instructions could also be useful to your future self.

You can also document commands to lint the code or run tests. These steps help to ensure high code quality and reduce the likelihood that the changes inadvertently break something. Having instructions for running tests is especially helpful if it requires external setup, such as starting a Selenium server for testing in a browser.

## Authors and acknowledgment
Show your appreciation to those who have contributed to the project.

## License
For open source projects, say how it is licensed.

## Project status
If you have run out of energy or time for your project, put a note at the top of the README saying that development has slowed down or stopped completely. Someone may choose to fork your project or volunteer to step in as a maintainer or owner, allowing your project to keep going. You can also make an explicit request for maintainers.

