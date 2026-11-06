# 프로필 장식 테두리 — 첫 업로드 기준 보정본

**전설 최신 동작:** [관절·겹침 수정본](assets/profile-borders-articulated-visible) · [원화 레이어와 동작 보기](assets/profile-borders-articulated-visible/index.html). 97번은 유지하고, 나머지 9종은 128px에서도 보이도록 동작 폭과 장식 표시 순서를 조정했습니다.

일반·고급·희귀·영웅에 적용할 파일은 **[assets/profile-borders-v1-repaired](assets/profile-borders-v1-repaired)**입니다.

[기존 100종 비교 화면](assets/profile-borders-v1-repaired/index.html) · [적용 방법](assets/profile-borders-v1-repaired/README.md)

기준은 두 번째 수정 후 처음 GitHub에 올린 [844e7c2의 PNG 100종](https://github.com/mangocrab/website-jeon_yong/tree/844e7c29e9e0fa80ff2d8c9fc89322eb059e66bf/assets/profile-borders)입니다. 기존 장식·색·구성을 유지하면서 찌그러진 비율을 보정했습니다. 비교 화면 왼쪽에서 해당 커밋의 실제 PNG를 확인할 수 있습니다.

| 등급 | 정지 PNG | 수량 | 효과·동작 |
|---|---|---:|---|
| 일반 | [normal](assets/profile-borders-v1-repaired/normal) | 30 | 정지, 그림 분리 없음 |
| 고급 | [premium](assets/profile-borders-v1-repaired/premium) | 25 | 정지, 그림 분리 없음 |
| 희귀 | [rare](assets/profile-borders-v1-repaired/rare) | 20 | 정지, 그림 분리 없음 |
| 영웅 | [epic](assets/profile-borders-v1-repaired/epic) | 15 | [후광·명암 이펙트 점멸](assets/profile-borders-v1-repaired/animations/epic), 완성 그림 한 장 유지 |
| 전설 | [legendary](assets/profile-borders-articulated-visible) | 10 | [독립 장식 동작·이펙트](assets/profile-borders-articulated-visible), 전설만 레이어 분리 |

PNG와 SVG 모두 1024×1024px, 중심 (512, 512), 안쪽 원 지름 716px입니다. 중앙은 완전 투명하며, SVG를 `<img>`로 표시하면 효과와 움직임을 재생합니다. ZIP 없이 개별 파일로 저장했습니다.

## 확인 및 재조립

```sh
python -m pip install -r tools/requirements.txt
python tools/build_v1_repair_animations.py
python tools/preview_v1_repairs.py
python -m pip install -r tools/browser-requirements.txt
python tools/validate_v1_repairs.py --browser /usr/bin/chromium
```

보정 PNG가 애니메이션의 입력입니다. 전설 레이어를 정지 상태로 합치면 해당 보정 PNG와 픽셀 단위로 일치해야 합니다. 검증 결과는 [validation.json](assets/profile-borders-v1-repaired/validation.json)에 있습니다.

## 이전 파일

- [처음 업로드한 PNG](assets/profile-borders)
- [이전 애니메이션](assets/profile-borders-animated)
- [별도 재디자인 V2](assets/profile-borders-v2): 이번 보정의 기준이나 적용 대상이 아닙니다.

기존 폴더는 보존하고, 이번 결과는 `assets/profile-borders-v1-repaired/`에 따로 저장합니다.
