
import requests
import hashlib
import re

from pathlib import Path
from io import BytesIO
from PIL import Image


def normalize(text):
    """대소문자, 공백, 특수문자 제거"""
    return re.sub(r'[\W_]+', '', str(text).casefold())


def get_album_art(title, singer):

    title = title.strip()
    singer = singer.strip()

    if not title or not singer:
        print("  └ 제목 또는 가수 이름이 비어 있음")
        return None

    # ==================================================
    # 1. 캐시 경로 설정
    # ==================================================

    # 현재 Python 파일이 있는 폴더 기준
    base_dir = (
        Path(__file__).resolve().parent
        if "__file__" in globals()
        else Path.cwd()
    )

    cache_dir = base_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # 가수 + 제목으로 고유한 캐시 파일명 생성
    cache_key = f"{normalize(singer)}|{normalize(title)}"

    cache_hash = hashlib.sha256(
        cache_key.encode("utf-8")
    ).hexdigest()[:12]

    safe_name = re.sub(
        r"[^\w-]+",
        "_",
        f"{singer}_{title}",
        flags=re.UNICODE
    ).strip("_")[:60]

    cache_file = cache_dir / f"{safe_name}_{cache_hash}.jpg"

    # ==================================================
    # 2. 캐시 확인
    # ==================================================

    if cache_file.exists():

        try:

            with Image.open(cache_file) as cached_image:

                image = cached_image.convert("RGB")

            print(f"  └ 캐시 이미지 사용: {cache_file}")
            return image

        except Exception as e:

            print(f"  └ 캐시 이미지 손상. 다시 다운로드합니다: {e}")

            cache_file.unlink()

    print("  └ 캐시에 이미지가 없습니다. 새로 검색합니다.")

    # ==================================================
    # 3. iTunes 검색
    # ==================================================

    search_url = "https://itunes.apple.com/search"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    session = requests.Session()

    try:

        results = []

        # KR 먼저 검색, 결과가 없으면 US 검색
        for country in ["KR", "US"]:

            params = {
                "term": f"{singer} {title}",
                "country": country,
                "media": "music",
                "entity": "song",
                "limit": 200
            }

            print(f"\n  └ iTunes 검색 중: {country}")

            try:

                response = session.get(
                    search_url,
                    params=params,
                    headers=headers,
                    timeout=30
                )

                response.raise_for_status()

                data = response.json()
                results = data.get("results", [])

                print(f"  └ 검색 결과: {len(results)}개")

            except (requests.RequestException, ValueError) as e:

                print(f"  └ 검색 실패: {e}")
                results = []

            # KR 결과가 있으면 US 검색 생략
            if results:
                break

            if country == "KR":
                print("  └ KR 결과 없음. US에서 재검색합니다.")

        if not results:

            print(f"  └ 검색 결과 없음: {title} - {singer}")
            return None

        # ==================================================
        # 4. 검색 결과 출력
        # ==================================================

        print("\n" + "=" * 80)
        print(f" 검색 결과: {title} - {singer}")
        print("=" * 80)

        for index, item in enumerate(results, start=1):
            print(f"[{index}] 곡 제목 : {item.get('trackName', '제목 없음')} - {item.get('artistName', '가수 미상')} || {item.get('collectionName', '앨범 정보 없음')}")

        print("\n" + "=" * 80)
        print(" 0. 취소")
        print("=" * 80)

        # ==================================================
        # 5. 사용자 선택
        # ==================================================

        if len(results) == 1:

            selected_track = results[0]

            print("\n  └ 검색 결과가 1개이므로 자동 선택합니다.")

        else:

            while True:

                choice = input("\n앨범을 선택하세요 (번호 입력): ").strip()

                if choice == "0":

                    print("  └ 앨범 선택을 취소했습니다.")
                    return None

                if not choice.isdigit():

                    print("  └ 숫자를 입력하세요.")
                    continue

                choice = int(choice)

                if 1 <= choice <= len(results):

                    selected_track = results[choice - 1]
                    break

                print(
                    f"  └ 1부터 {len(results)} 사이의 번호를 입력하세요."
                )

        # ==================================================
        # 6. 선택한 곡 정보
        # ==================================================

        print("\n" + "=" * 80)
        print(" 선택된 곡")
        print("=" * 80)

        print(f"  곡 제목 : {selected_track.get('trackName')}")
        print(f"  가수    : {selected_track.get('artistName')}")
        print(f"  앨범    : {selected_track.get('collectionName')}")

        # ==================================================
        # 7. 앨범 커버 다운로드
        # ==================================================

        image_url = (
            selected_track.get("artworkUrl100")
            or selected_track.get("artworkUrl60")
        )

        if not image_url:

            print("  └ 앨범 이미지 URL이 없습니다.")
            return None

        # 600x600 이미지 요청
        large_image_url = re.sub(
            r"/\d+x\d+bb(?=\.)",
            "/600x600bb",
            image_url
        )

        print("\n  └ 앨범 커버 다운로드 중...")

        try:

            image_response = session.get(
                large_image_url,
                headers=headers,
                timeout=30
            )

            image_response.raise_for_status()

        except requests.RequestException:

            print("  └ 고해상도 다운로드 실패. 원본으로 재시도합니다.")

            image_response = session.get(
                image_url,
                headers=headers,
                timeout=30
            )

            image_response.raise_for_status()

        image = Image.open(
            BytesIO(image_response.content)
        ).convert("RGB")

        # ==================================================
        # 8. 캐시 저장
        # ==================================================

        image.save(
            cache_file,
            format="JPEG",
            quality=95,
            optimize=True
        )

        print(f"  └ 다운로드 완료: {image.size}")
        print(f"  └ 캐시 저장 완료: {cache_file}")

        return image

    except Exception as e:

        print(f"  └ 앨범 커버 가져오기 실패: {e}")
        return None

    finally:

        session.close()


# ==================================================
# 테스트
# ==================================================

image = get_album_art(
    "거울",
    "국카스텐"
)

if image:
    image.show()
