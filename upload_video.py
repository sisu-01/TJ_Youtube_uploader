import os
import google.oauth2.credentials
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
import pickle

# 설정 (다운로드한 JSON 파일 이름과 일치해야 함)
CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = ['https://www.googleapis.com/auth/youtube']

def get_authenticated_service():
    creds = None
    # 이전에 인증한 정보가 저장된 파일(token.pickle)이 있는지 확인
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # 인증 정보가 없거나 유효하지 않으면 새로 인증
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # 새로운 인증 정보를 다음에 사용하기 위해 저장
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('youtube', 'v3', credentials=creds)

def upload_to_youtube(video_path, title, description, playlist_id=None):
    # 1. 인증된 서비스 객체 생성 (여기서 creds가 정의됨)
    youtube = get_authenticated_service()

    # 2. 업로드할 비디오 정보 설정
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': ['karaoke', 'TJ'],
            'categoryId': '10' # Music
        },
        'status': {
            'privacyStatus': 'unlisted' # 처음엔 비공개로 올리는 것을 추천
        }
    }

    # 3. 파일 전송 설정 (resumable=True는 대용량 파일에 필수)
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    
    request = youtube.videos().insert(
        part=','.join(body.keys()),
        body=body,
        media_body=media
    )

    print(f"--- 유튜브 업로드 시작: {title} ---")
    
    # 4. 실제 업로드 실행
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"업로드 중... {int(status.progress() * 100)}%")

    video_id = response['id']
    print(f"✅ 업로드 완료! 비디오 ID: {response['id']}")
    print(f"확인 링크: https://youtu.be/{response['id']}")

    # 2. 특정 재생목록에 추가 (Playlist ID가 있을 경우)
    if playlist_id:
        add_to_playlist(youtube, video_id, playlist_id)

def add_to_playlist(youtube, video_id, playlist_id):
    """영상을 특정 재생목록에 추가하는 함수"""
    try:
        request = youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id
                    }
                }
            }
        )
        request.execute()
        print(f"📂 재생목록에 추가 완료! (ID: {playlist_id})")
    except Exception as e:
        print(f"❌ 재생목록 추가 중 오류 발생: {e}")