import streamlit as st
import time
import csv
from datetime import datetime
from atproto import Client, models

st.set_page_config(page_title="Bluesky Blocker", page_icon="🚫")

st.title("🚫 Bluesky Follower Blocker")
st.markdown("Block users who follow more than a certain number of accounts. Works using your own Bluesky credentials.")

# === USER INPUT ===
username = st.text_input("Your Bluesky Username", placeholder="yourname.bsky.social")
app_password = st.text_input("App Password", type="password")
seed_user = st.text_input("Target Account to Analyze (Seed User)", value="aykuterdogdu.bsky.social")
min_follows = st.slider("Minimum number of followings to block", min_value=1000, max_value=10000, value=3000)

run_button = st.button("🚀 Start Blocking")

# === CSV OUTPUT SETUP ===
CSV_FILENAME = "blocked_users_log.csv"
FIELDNAMES = ["Handle", "Follows Count", "DID", "Blocked At"]

def save_to_csv(user):
    with open(CSV_FILENAME, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerow(user)

# === CORE FUNCTION ===
if run_button and username and app_password:
    st.success("Logging in and fetching followers...")

    client = Client()
    try:
        client.login(username, app_password)
    except Exception as e:
        st.error(f"Login failed: {e}")
        st.stop()

    try:
        followers = client.app.bsky.graph.get_followers({'actor': seed_user, 'limit': 100}).followers
    except Exception as e:
        st.error(f"Failed to fetch followers of @{seed_user}: {e}")
        st.stop()

    st.info(f"Fetched {len(followers)} followers. Filtering users with >{min_follows} followings...")

    blocked = 0
    with open(CSV_FILENAME, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()

    for user in followers:
        follows_count = getattr(user, "follows_count", 0)
        if follows_count >= min_follows:
            try:
                client.app.bsky.graph.block.create(
                    repo=client.me.did,
                    record=models.AppBskyGraphBlock.Record(
                        subject=user.did,
                        created_at=datetime.utcnow().isoformat() + "Z"
                    )
                )
                blocked += 1
                st.write(f"🚫 Blocked @{user.handle} ({follows_count} following)")
                save_to_csv({
                    "Handle": user.handle,
                    "Follows Count": follows_count,
                    "DID": user.did,
                    "Blocked At": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                })
                time.sleep(2)  # small delay to be nice to the API
            except Exception as e:
                st.warning(f"⚠️ Failed to block @{user.handle}: {e}")

    st.success(f"✅ Finished. {blocked} users blocked.")
    st.download_button("📥 Download Block Log", data=open(CSV_FILENAME, "rb"), file_name=CSV_FILENAME)

elif run_button:
    st.warning("Please enter your Bluesky credentials.")
