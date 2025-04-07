import streamlit as st
import time
import csv
from datetime import datetime
from atproto import Client, models

st.set_page_config(page_title="Bluesky Blocker", page_icon="🚫")
st.title("🚫 Bluesky Follower Blocker")

st.markdown("""
Block users who follow more than a certain number of accounts.  
All actions use **your own Bluesky credentials** — nothing is stored or shared.
""")

# === USER INPUT ===
username = st.text_input("Your Bluesky Username", placeholder="yourname.bsky.social")
app_password = st.text_input("App Password", type="password", placeholder="You can generate this at https://bsky.app/settings/app-passwords")
min_follows = st.slider("Minimum number of followings to consider for blocking", min_value=1000, max_value=20000, value=3000)
max_profiles = st.number_input("Maximum number of followers to scan (for performance)", min_value=10, max_value=1000, value=200, step=10)

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    run_button = st.button("🚀 Start Scanning", use_container_width=True)

CSV_FILENAME = "blocked_users_log.csv"
FIELDNAMES = ["Handle", "Follows Count", "DID", "Blocked At"]

def save_to_csv(user):
    with open(CSV_FILENAME, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerow(user)

def get_all_followers(client, actor, limit):
    followers = []
    cursor = None
    try:
        while len(followers) < limit:
            res = client.app.bsky.graph.get_followers({'actor': actor, 'limit': 100, 'cursor': cursor})
            followers.extend(res.followers)
            if hasattr(res, 'cursor') and res.cursor:
                cursor = res.cursor
            else:
                break
    except Exception as e:
        st.error(f"❌ Failed to fetch followers: {e}")
    return followers[:limit]

def get_blocked_dids(client):
    blocked_dids = set()
    cursor = None
    try:
        while True:
            res = client.app.bsky.graph.get_blocks({'limit': 100, 'cursor': cursor})
            blocked_dids.update([b.did for b in res.blocks])
            if hasattr(res, 'cursor') and res.cursor:
                cursor = res.cursor
            else:
                break
    except Exception as e:
        st.warning(f"⚠️ Could not retrieve block list: {e}")
    return blocked_dids

if run_button and username and app_password:
    st.warning("⏳ This may take a few minutes. We'll fetch your followers and profile info, please wait...")

    client = Client()
    try:
        client.login(username, app_password)
    except Exception as e:
        st.error(f"❌ Login failed: {e}")
        st.stop()

    st.info("🔍 Fetching your current block list...")
    blocked_dids = get_blocked_dids(client)

    st.info(f"📥 Fetching up to {max_profiles} followers of @{username}...")
    followers = get_all_followers(client, username, max_profiles)

    eligible = []

    progress_bar = st.progress(0)
    for i, user in enumerate(followers):
        try:
            profile = client.app.bsky.actor.get_profile({'actor': user.did})
            if profile.follows_count >= min_follows and user.did not in blocked_dids:
                eligible.append({
                    "handle": user.handle,
                    "did": user.did,
                    "follows_count": profile.follows_count
                })
        except Exception as e:
            st.warning(f"⚠️ Could not fetch profile for @{user.handle}: {e}")
        progress_bar.progress((i + 1) / len(followers))

    progress_bar.empty()
    st.success(f"✅ Found {len(eligible)} new user(s) to potentially block.")

    if eligible:
        num_to_block = st.slider("How many users do you want to block?", 1, len(eligible), value=min(len(eligible), 50))
        confirm = st.button("🚫 Block Now")

        if confirm:
            st.info("🚫 Blocking users... please wait...")

            blocked = 0
            with open(CSV_FILENAME, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
                writer.writeheader()

            for user in eligible[:num_to_block]:
                try:
                    client.app.bsky.graph.block.create(
                        repo=client.me.did,
                        record=models.AppBskyGraphBlock.Record(
                            subject=user["did"],
                            created_at=datetime.utcnow().isoformat() + "Z"
                        )
                    )
                    blocked += 1
                    st.write(f"✅ Blocked @{user['handle']} ({user['follows_count']} following)")
                    save_to_csv({
                        "Handle": user["handle"],
                        "Follows Count": user["follows_count"],
                        "DID": user["did"],
                        "Blocked At": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    time.sleep(2)
                except Exception as e:
                    st.warning(f"⚠️ Failed to block @{user['handle']}: {e}")

            st.success(f"🎉 Done. {blocked} new user(s) blocked.")
            st.download_button("📥 Download Block Log", data=open(CSV_FILENAME, "rb"), file_name=CSV_FILENAME)

    else:
        st.info("No new users found who match the criteria.")

elif run_button:
    st.warning("Please enter your Bluesky credentials.")
