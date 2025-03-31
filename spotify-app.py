import requests
from flask import Flask, request, redirect, jsonify, send_file, session
import os

app = Flask(__name__)

# Secret key for session management
app.secret_key = 'random_secret_key_for_sessions'

CLIENT_ID = '5dd4a74df7a34ef085a14961317b222e'
CLIENT_SECRET = 'f2ddfcc48beb46649c5fe46a98bcc994'
REDIRECT_URI = 'http://127.0.0.1:8888/callback'
SCOPE = 'user-library-read'

@app.route('/')
def home():
    return redirect('/login')

@app.route('/login')
def login():
    auth_url = f"https://accounts.spotify.com/authorize?response_type=code&client_id={CLIENT_ID}&scope={SCOPE}&redirect_uri={REDIRECT_URI}"
    return redirect(auth_url)

@app.route('/callback')
def callback():
    # Get the authorization code from the URL
    code = request.args.get('code')
    token_url = "https://accounts.spotify.com/api/token"
    
    # Request an access token using the authorization code
    response = requests.post(token_url, data={
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }, headers={'Content-Type': 'application/x-www-form-urlencoded'})

    token_info = response.json()
    access_token = token_info.get('access_token')
    
    # Get the user’s Spotify ID to identify the user
    user_info = get_user_info(access_token)
    user_id = user_info.get('id')

    # Store the access token and user ID in the session
    session['access_token'] = access_token
    session['user_id'] = user_id
    
    # Get liked songs for this user
    liked_songs = get_liked_songs(access_token)

    # Check if the file for this user exists and handle accordingly
    file_path = f"{user_id}_liked_songs.txt"
    existing_songs = []

    if os.path.exists(file_path):
        # Read the existing songs from the file
        with open(file_path, 'r') as file:
            existing_songs = set(file.read().splitlines())

    # Filter out the new songs that are already in the existing file
    new_songs = [song for song in liked_songs if song not in existing_songs]

    if new_songs:
        # If there are new songs, save them to the file
        file_path = save_songs_to_file(user_id, new_songs, existing_songs)
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({"message": "No new songs found. The file is up-to-date."})

def get_user_info(access_token):
    url = "https://api.spotify.com/v1/me"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    response = requests.get(url, headers=headers)
    return response.json()

def get_liked_songs(access_token):
    url = 'https://api.spotify.com/v1/me/tracks'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    
    song_list = []
    offset = 0
    limit = 50  # You can request up to 50 items per request

    while True:
        response = requests.get(f"{url}?limit={limit}&offset={offset}", headers=headers)
        
        if response.status_code == 200:
            tracks = response.json()
            items = tracks.get('items', [])
            if not items:
                break  # Exit the loop if there are no more items
            for item in items:
                track = item['track']
                song_list.append(f"{track['name']} by {', '.join(artist['name'] for artist in track['artists'])}")
            offset += limit  # Move to the next set of results
        else:
            return {'error': f"Error: {response.status_code}"}

    return song_list

def save_songs_to_file(user_id, new_songs, existing_songs):
    file_path = f"{user_id}_liked_songs.txt"
    # Combine the existing songs and the new songs, then save to the file
    all_songs = set(existing_songs) | set(new_songs)  # Union to avoid duplicates
    with open(file_path, 'w') as file:
        for song in all_songs:
            file.write(f"{song}\n")
    return file_path

if __name__ == '__main__':
    app.run(port=8888)
