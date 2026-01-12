
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

def list_teams():
    token = os.getenv("FIGMA_ACCESS_TOKEN")
    if not token:
        print("Error: No token found")
        return

    print("Fetching your teams...")
    # Get current user first to verify token
    me_resp = requests.get("https://api.figma.com/v1/me", headers={"X-Figma-Token": token})
    if me_resp.status_code != 200:
        print("Error fetching user info:", me_resp.text)
        return
    
    user = me_resp.json()
    print(f"User: {user.get('handle')} ({user.get('email')}) - ID: {user.get('id')}")
    user_id = user.get('id')

    # Get Teams
    # Note: Figma API doesn't have a direct "list my teams" endpoint easily accessible with a PAT sometimes, 
    # but let's try the common endpoint or iterating if needed.
    # Actually, the best way with a PAT is to look at the user's generic info or just ask the user.
    # But wait, there is `GET /v1/teams/:team_id` if we know it.
    # There isn't a simple "list all my teams" endpoint for PATs in the public documentation easily?
    # Let's try `GET /v1/me/teams` which is often available.
    
    response = requests.get(f"https://api.figma.com/v1/teams", headers={"X-Figma-Token": token}) 
    # This endpoint doesn't exist.
    
    # Correct endpoint is `GET /v1/users/:id/teams`
    teams_url = f"https://api.figma.com/v1/users/{user_id}/teams"
    teams_resp = requests.get(teams_url, headers={"X-Figma-Token": token})
    
    if teams_resp.status_code == 200:
        teams = teams_resp.json()
        print("\nFound Teams:")
        for t in teams:
            print(f"- {t.get('name')} (ID: {t.get('id')})")
    else:
        print("Error fetching teams:", teams_resp.text)

if __name__ == "__main__":
    list_teams()
