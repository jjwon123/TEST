# Correction Summary - cosmetics_skincare_pinterest_holdout_003

- Profile: `cosmetics_skincare`
- Reviewed: 31/31
- Accuracy: 0.484
- Final distribution: {'selected': 7, 'shortlist': 16, 'rejected': 8}
- Transitions: {'rejected->rejected': 4, 'rejected->selected': 3, 'rejected->shortlist': 5, 'selected->selected': 1, 'selected->shortlist': 1, 'shortlist->rejected': 4, 'shortlist->selected': 3, 'shortlist->shortlist': 10}
- Reason tags: {'low_resolution': 2}

## Learned Rules

- `hard_reject_visual_defects`: 저해상도, 웹페이지 캡처, 카테고리 오류, 가짜 텍스트 위험은 selected로 올리지 않는다.
- `soften_rejected_to_shortlist`: 명확한 hard reject 신호가 없고 부분 참고 가치가 있으면 rejected보다 shortlist를 우선한다.

## Reviewed Examples

- `cosmetics_skincare_ref_01` selected -> shortlist | tags: - | 빠른 비교에서 둘 다 참고 후보
- `cosmetics_skincare_ref_02` shortlist -> shortlist | tags: - | 빠른 비교에서 둘 다 참고 후보
- `cosmetics_skincare_ref_03` rejected -> rejected | tags: low_resolution | 빠른 비교에서 상대적으로 부적합
- `cosmetics_skincare_ref_04` selected -> selected | tags: - | 빠른 비교에서 더 적합한 레퍼런스로 선택
- `cosmetics_skincare_ref_05` shortlist -> selected | tags: - | 빠른 비교에서 더 적합한 레퍼런스로 선택
- `cosmetics_skincare_ref_06` rejected -> rejected | tags: low_resolution | 빠른 비교에서 상대적으로 부적합
- `cosmetics_skincare_ref_07` shortlist -> selected | tags: - | 빠른 비교에서 더 적합한 레퍼런스로 선택
- `cosmetics_skincare_ref_08` rejected -> rejected | tags: - | 빠른 비교에서 상대적으로 부적합
- `cosmetics_skincare_ref_09` shortlist -> rejected | tags: - | 여러 이미지가 들어잇는 하나의 이미지
- `cosmetics_skincare_ref_10` rejected -> selected | tags: - | 빠른 비교에서 더 적합한 레퍼런스로 선택
- `cosmetics_skincare_ref_11` shortlist -> shortlist | tags: - | 빠른 비교에서 둘 다 참고 후보
- `cosmetics_skincare_ref_12` rejected -> shortlist | tags: - | 빠른 비교에서 둘 다 참고 후보
- `cosmetics_skincare_ref_13` shortlist -> shortlist | tags: - | 빠른 비교에서 둘 다 참고 후보
- `cosmetics_skincare_ref_14` rejected -> shortlist | tags: - | 빠른 비교에서 둘 다 참고 후보
- `cosmetics_skincare_ref_15` shortlist -> rejected | tags: - | 빠른 비교에서 상대적으로 부적합
- `cosmetics_skincare_ref_16` rejected -> selected | tags: - | 빠른 비교에서 더 적합한 레퍼런스로 선택
- `cosmetics_skincare_ref_17` shortlist -> shortlist | tags: - | 빠른 비교에서 둘 다 참고 후보
- `cosmetics_skincare_ref_18` rejected -> shortlist | tags: - | 빠른 비교에서 둘 다 참고 후보
- `cosmetics_skincare_ref_19` shortlist -> rejected | tags: - | 빠른 비교에서 둘 다 제외
- `cosmetics_skincare_ref_20` rejected -> rejected | tags: - | 빠른 비교에서 둘 다 제외
- `cosmetics_skincare_ref_21` shortlist -> shortlist | tags: - | 빠른 비교에서 둘 다 참고 후보
- `cosmetics_skincare_ref_22` rejected -> shortlist | tags: - | 빠른 비교에서 둘 다 참고 후보
- `cosmetics_skincare_ref_23` shortlist -> shortlist | tags: - | 빠른 비교에서 둘 다 참고 후보
- `cosmetics_skincare_ref_24` rejected -> shortlist | tags: - | 빠른 비교에서 둘 다 참고 후보
- `cosmetics_skincare_ref_25` shortlist -> rejected | tags: - | 빠른 비교에서 상대적으로 부적합
- `cosmetics_skincare_ref_26` rejected -> selected | tags: - | 빠른 비교에서 더 적합한 레퍼런스로 선택
- `cosmetics_skincare_ref_27` shortlist -> shortlist | tags: - | 빠른 비교에서 둘 다 참고 후보
- `cosmetics_skincare_ref_28` shortlist -> shortlist | tags: - | 빠른 비교에서 둘 다 참고 후보
- `cosmetics_skincare_ref_29` shortlist -> shortlist | tags: - | 빠른 비교에서 둘 다 참고 후보
- `cosmetics_skincare_ref_30` shortlist -> shortlist | tags: - | 빠른 비교에서 둘 다 참고 후보
- `cosmetics_skincare_ref_31` shortlist -> selected | tags: - | 빠른 비교에서 더 적합한 레퍼런스로 선택
