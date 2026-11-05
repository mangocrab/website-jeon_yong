# 프로필 장식 테두리 — 최신 V2

**현재 수정본: [assets/profile-borders-v2](assets/profile-borders-v2)**

[실제 V2 미리보기](assets/profile-borders-v2/index.html) · [적용 방법·개별 레이어 안내](assets/profile-borders-v2/README.md)

전체 100종을 새 장식 레이어로 다시 구성했습니다.
테두리와 장식을 독립적으로 만들고, 장식은 원래 가로·세로 비율을 유지해 배치합니다.
영웅·전설 이펙트에는 후광과 명암을 넣었고, 전설은 별도로 그린 개별 장식 PNG를 연결해 움직입니다.

| 등급 | 최신 정지 파일 | 수량 | 효과·동작 |
|---|---|---:|---|
| 일반 | [normal](assets/profile-borders-v2/normal) | 30 | 정지 |
| 고급 | [premium](assets/profile-borders-v2/premium) | 25 | 정지 |
| 희귀 | [rare](assets/profile-borders-v2/rare) | 20 | 정지 |
| 영웅 | [epic](assets/profile-borders-v2/epic) | 15 | [이펙트 SVG](assets/profile-borders-v2/animations/epic) |
| 전설 | [legendary](assets/profile-borders-v2/legendary) | 10 | [개별 레이어 동작 SVG](assets/profile-borders-v2/animations/legendary) |

공통 규격은 1024×1024px, 중심 (512, 512), 안쪽 원 지름 716px, 중앙 완전 투명입니다.
PNG는 정지 조립본이고, 후광·명암 효과와 움직임은 animations의 SVG로 사용합니다.
SVG는 일반 img 태그로 표시할 수 있으며 필요한 모든 그림이 파일 안에 포함돼 있습니다.

[layers](assets/profile-borders-v2/layers)에는 테두리 PNG 100개와 새로 그린 장식 PNG 300개가 있습니다.
전설 한 종류마다 테두리 1개와 장식 9개가 독립돼 있습니다.
미리보기의 ‘독립 레이어’에서 각각 확인하고 다운로드할 수 있습니다. ZIP은 만들지 않았습니다.

## 편집·재생성

```sh
python -m pip install -r tools/requirements.txt
python tools/build_profile_v2.py --from-layers
python tools/build_profile_v2_preview.py
```

브라우저 검증:

```sh
python -m pip install -r tools/browser-requirements.txt
python tools/validate_profile_v2.py --browser /usr/bin/chromium
```

검증 결과는 [V2 validation.json](assets/profile-borders-v2/validation.json)에 있습니다.

## 이전 버전 보존

- [기존 PNG 100종](assets/profile-borders)
- [기존 애니메이션 25종](assets/profile-borders-animated)

이전 파일은 덮어쓰지 않았습니다. 새 적용 경로는 assets/profile-borders-v2/입니다.
