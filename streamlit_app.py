import streamlit as st
import time
import csv
from datetime import datetime
from atproto import Client, models

st.set_page_config(page_title="Bluesky Blocker", page_icon="🚫")
st.title("🚫 Bluesky Follower Blocker")

st.markdown("Block users who follow more than a certain number of accounts.\n"
            "All actions use **your own Bluesky credentials** — nothing is stored or shared.")

# === USER INPUT ===
username = st.text_input("Your Bluesky Username", placeholder="yourname.bsky.social")
app_password = st.text_input("App Password", type="password", placeholder="You can generate this at https://bsky.app/settings/app-passwords")
min_follows = st.slider("Minimum number of followings to consider for blocking", min_value=1000, max_value=10000, value=3000)

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    run_button = st.button("🚀 Start Scanning", use_container_width=True)

# === CSV SETUP ===
CSV_FILENAME = "blocked_users_log.csv"
FIELDNAMES = ["Handle", "Follows Count", "DID", "Blocked At"]

def save_to_csv(user):
    with open(CSV_FILENAME, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerow(user)

# === MAIN WORKFLOW ===
if run_button and username and app_password:
    st.success("Logging in...")
    client = Client()

    try:
        client.login(username, app_password)
    except Exception as e:
        st.error(f"❌ Login failed: {e}")
        st.stop()

    st.info(f"Fetching followers of @{username}...")

    try:
        followers = client.app.bsky.graph.get_followers({'actor': username, 'limit': 100}).followers
    except Exception as e:
        st.error(f"❌ Failed to fetch followers: {e}")
        st.stop()

    eligible = [u for u in followers if getattr(u, "follows_count", 0) >= min_follows]

    st.success(f"✅ Found {len(eligible)} user(s) with more than {min_follows} followings.")

    if eligible:
        num_to_block = st.slider("How many users do you want to block?", 1, len(eligible), value=len(eligible))
        confirm = st.button("🚫 Block Now")

        if confirm:
            st.info("Starting block process...")
            blocked = 0

            with open(CSV_FILENAME, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
                writer.writeheader()

            for user in eligible[:num_to_block]:
                try:
                    client.app.bsky.graph.block.create(
                        repo=client.me.did,
                        record=models.AppBskyGraphBlock.Record(
                            subject=user.did,
                            created_at=datetime.utcnow().isoformat() + "Z"
                        )
                    )
                    blocked += 1
                    st.write(f"🚫 Blocked @{user.handle} ({user.follows_count} following)")
                    save_to_csv({
                        "Handle": user.handle,
                        "Follows Count": user.follows_count,
                        "DID": user.did,
                        "Blocked At": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    time.sleep(2)
                except Exception as e:
                    st.warning(f"⚠️ Failed to block @{user.handle}: {e}")

            st.success(f"🎉 Done. {blocked} user(s) blocked.")
            st.download_button("📥 Download Block Log", data=open(CSV_FILENAME, "rb"), file_name=CSV_FILENAME)
    else:
        st.info("No users found who match the criteria.")

elif run_button:
    st.warning("Please enter your Bluesky credentials.")
