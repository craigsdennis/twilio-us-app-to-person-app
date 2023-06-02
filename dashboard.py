import dateutil
import datetime
import os

import pandas as pd
import streamlit as st
from twilio.rest import Client

US_A2P_CAMPAIGN_SID = "QE2c6890da8086d771620e9b13fadeba0b"

"# A2P 10DLC Dashboard"

with st.sidebar:
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID", None)
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN", None)

    if account_sid is None or auth_token is None:
        "## Twilio Account Information"
        account_sid = st.text_input("Account SID")
        auth_token = st.text_input("Auth Token", type="password")
    if not account_sid or not auth_token:
        st.warning("To get started, please provide your Twilio credentials")
        st.stop()
    f"**Account SID** : `{account_sid}`"
    client = Client(account_sid, auth_token)

setup_progress_bar = st.progress(0, "Getting started...")

current_step = 0
TOTAL_SETUP_STEP_COUNT = 5

def update_progress(text):
    global current_step
    current_step = current_step + 1
    if current_step >= TOTAL_SETUP_STEP_COUNT:
        setup_progress_bar.empty()
        return
    pct = (current_step / TOTAL_SETUP_STEP_COUNT)
    setup_progress_bar.progress(pct, text)

# TODO: Break into utils
@st.cache_data
def twilio_objects_dataframe(_objects, key, attributes, index_attr="sid"):
    print(f"caching {key}")
    values = [[getattr(obj, a) for a in attributes] for obj in _objects]
    return pd.DataFrame(
        values, columns=attributes, index=(getattr(obj, index_attr) for obj in _objects)
    )


@st.cache_data
def fetch_messaging_services():
    return client.messaging.v1.services.list()


update_progress("Gathering Messaging Services...")
messaging_services = fetch_messaging_services()
messaging_services_df = twilio_objects_dataframe(
    messaging_services,
    "messaging_services",
    (
        "friendly_name",
        "usecase",
        "us_app_to_person_registered",
    ),
)

@st.cache_data
def fetch_all_phone_numbers():
    return client.incoming_phone_numbers.list()


update_progress("Gathering all phone numbers")
phone_numbers = fetch_all_phone_numbers()
phone_numbers_df = twilio_objects_dataframe(
    phone_numbers,
    "phone_numbers",
    ("phone_number", "friendly_name"),
)
phone_numbers_df["us_a2p_registered"] = False


for ms in messaging_services:
    phone_numbers = ms.phone_numbers.list()
    for phone_number in phone_numbers:
        phone_numbers_df.loc[
            phone_numbers_df.phone_number == phone_number.phone_number,
            ["messaging_service_sid", "us_a2p_registered", "messaging_service_friendly_name", "messaging_service_usecase"],
        ] = (ms.sid, ms.us_app_to_person_registered, ms.friendly_name, ms.usecase)
    campaigns = ms.us_app_to_person.list()
    if campaigns:
        # TODO: We could search...why is this a list?
        campaign = campaigns[0]
        phone_numbers_df.loc[
            phone_numbers_df.messaging_service_sid == ms.sid,
            ["campaign_status", "us_app_to_person_usecase", "brand_registration_sid"],
        ] = (campaign.campaign_status, campaign.us_app_to_person_usecase, campaign.brand_registration_sid)

@st.cache_data
def get_messaging_stats_for_number(phone_number):
    messages = client.messages.list(from_=phone_number, limit=100)
    if not messages:
        return (0, None)
    return (len(messages), messages[0].date_created)


def add_message_stats(row):
    stats = get_messaging_stats_for_number(row["phone_number"])
    return pd.Series(stats)


@st.cache_data
def get_us_numbers_with_stats(_phone_numbers_df):
    # Gather the US numbers and copy the df
    us_numbers_df = phone_numbers_df.loc[
        phone_numbers_df.phone_number.str.startswith("+1")
    ].copy()
    # Add columns...
    us_numbers_df[["message_count", "last_message_sent_date"]] = us_numbers_df.apply(
        add_message_stats, axis=1
    )
    us_numbers_df = us_numbers_df.sort_values(
        by=["last_message_sent_date"], ascending=False
    )
    return us_numbers_df


update_progress("Collecting stats on US Numbers...")
us_numbers_df = get_us_numbers_with_stats(phone_numbers_df)

def link_for_sid(sid):
    if sid.startswith("PN"):
        return f"https://console.twilio.com/us1/develop/phone-numbers/manage/incoming/{sid}/configure"
    if sid.startswith("MG"):
        return f"https://console.twilio.com/us1/service/sms/{sid}/sms-senders"

def active_number_row_template(sid, row):
    delta = pd.Timestamp.now(tz="utc") - row["last_message_sent_date"]
    return f"[{row['friendly_name']}: {row['phone_number']}]({link_for_sid(sid)}) ({int(row['message_count'])} total outbound messages, last sent {delta.days} days ago)"

update_progress("Checking for active US numbers not in messaging services...")
unserviced_df = us_numbers_df[us_numbers_df.messaging_service_sid.isnull() & us_numbers_df.message_count > 0]
if len(unserviced_df):
    st.warning(f"You have {len(unserviced_df)} **active** US phone numbers not currently in a Messaging Service")
    for index, row in unserviced_df.iterrows():
        st.write(active_number_row_template(index, row))

update_progress("Checking for Messaging Services that are unregistered with US numbers")
unregistered_df = us_numbers_df.loc[us_numbers_df.messaging_service_sid.notnull() & us_numbers_df.message_count > 0]
unregistered_df = unregistered_df[unregistered_df.us_a2p_registered == False]
#unregistered_df = unregistered_df[]
if len(unregistered_df):
    st.warning(f"You have {unregistered_df.messaging_service_sid.nunique()} unregistered for A2P 10DLC Messaging Services with active US numbers")
    # unregistered_df.sort_values(by="messaging_service_sid")
    previous_friendly_name = None
    for index, row in unregistered_df.iterrows():
        current_friendly_name = row["messaging_service_friendly_name"]
        if current_friendly_name != previous_friendly_name:
            st.write(f"[{current_friendly_name}]({link_for_sid(row['messaging_service_sid'])})")
            st.markdown = f"[**{current_friendly_name}**]({link_for_sid(row['messaging_service_sid'])})"
            current_friendly_name = previous_friendly_name
        st.write("- " + active_number_row_template(index, row))


with st.expander("For debugging only"):
    us_numbers_df 


# brands = client.messaging.v1.brand_registrations.list()
# brands_df = twilio_objects_dataframe(brands, (
#     "status",
#     "brand_score",
#     "brand_type",
# ))
# brands_df