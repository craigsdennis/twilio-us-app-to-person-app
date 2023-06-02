# US App to Person App

⚠️ This is very much a work in progress

An exploratory tool to use the Twilio API to determine compliance needs for A2P 10DLC.

## Installation

Requires Python > 3.8 [Install](https://python.org)


Copy `.env.example` to `.env` and update with the key.

```bash
python -m venv venv
source ./venv/bin/activate
python -m pip install -r requirements.txt
```

## Run the app

```
streamlit run dasboard.py
```

## About

This is using the [pandas](https://pandas.pydata.org/) library to create `DataFrame`s that store information from the [Twilio Compliance APIs](https://www.twilio.com/docs/sms/a2p-10dlc)
