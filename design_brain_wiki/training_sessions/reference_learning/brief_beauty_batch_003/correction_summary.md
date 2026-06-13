# Correction Summary - reference_learning_brief_beauty_batch_003

- Profile: `reference_learning`
- Reviewed: 31/50
- Accuracy: 0.194
- Final distribution: {'selected': 8, 'shortlist': 6, 'rejected': 17}
- Transitions: {'rejected->rejected': 2, 'rejected->selected': 2, 'rejected->shortlist': 2, 'selected->rejected': 2, 'shortlist->rejected': 13, 'shortlist->selected': 6, 'shortlist->shortlist': 4}
- Reason tags: {}

## Learned Rules

- `soften_rejected_to_shortlist`: 명확한 hard reject 신호가 없고 부분 참고 가치가 있으면 rejected보다 shortlist를 우선한다.

## Reviewed Examples

- `learning_ref_d0f6768ea3a1` shortlist -> rejected | tags: - | 빠른 비교에서 둘 다 제외
- `learning_ref_6ebd6f20f2d8` shortlist -> shortlist | tags: - | 빠른 비교에서 둘 다 참고 후보
- `learning_ref_d219a3fdf501` shortlist -> shortlist | tags: - | 빠른 비교에서 둘 다 참고 후보
- `learning_ref_85bd9d29dbda` shortlist -> rejected | tags: - | 빠른 비교에서 상대적으로 부적합
- `learning_ref_87cc87cec531` shortlist -> selected | tags: - | 빠른 비교에서 더 적합한 레퍼런스로 선택
- `learning_ref_e2544587bb4b` rejected -> rejected | tags: - | 빠른 비교에서 둘 다 제외
- `learning_ref_ed899af2292b` shortlist -> rejected | tags: - | 빠른 비교에서 둘 다 제외
- `learning_ref_89461a53ca14` shortlist -> selected | tags: - | 빠른 비교에서 더 적합한 레퍼런스로 선택
- `learning_ref_f0cc9050bbd2` shortlist -> rejected | tags: - | 빠른 비교에서 상대적으로 부적합
- `learning_ref_f16c671029cf` selected -> rejected | tags: - | 빠른 비교에서 둘 다 제외
- `learning_ref_8c6bd288e408` shortlist -> rejected | tags: - | 빠른 비교에서 둘 다 제외
- `learning_ref_f6fe77846f64` selected -> rejected | tags: - | 빠른 비교에서 상대적으로 부적합
- `learning_ref_8d8216912745` shortlist -> selected | tags: - | 빠른 비교에서 더 적합한 레퍼런스로 선택
- `learning_ref_f79cdb1cbeee` shortlist -> rejected | tags: - | 빠른 비교에서 상대적으로 부적합
- `learning_ref_8d85fedbe7b0` shortlist -> selected | tags: - | 빠른 비교에서 더 적합한 레퍼런스로 선택
- `learning_ref_f9e27c855058` shortlist -> rejected | tags: - | 빠른 비교에서 둘 다 제외
- `learning_ref_fefd411b68e2` shortlist -> rejected | tags: - | 빠른 비교에서 둘 다 제외
- `learning_ref_906187de015f` rejected -> selected | tags: - | 빠른 비교에서 더 적합한 레퍼런스로 선택
- `learning_ref_9229c9a1d260` shortlist -> rejected | tags: - | 빠른 비교에서 상대적으로 부적합
- `learning_ref_963db02e26ec` shortlist -> rejected | tags: - | 빠른 비교에서 상대적으로 부적합
- `learning_ref_9897b55a1a6a` shortlist -> selected | tags: - | 빠른 비교에서 더 적합한 레퍼런스로 선택
- `learning_ref_9f65e958c346` rejected -> rejected | tags: - | 빠른 비교에서 둘 다 제외
- `learning_ref_9fc1a72735ec` shortlist -> rejected | tags: - | 빠른 비교에서 둘 다 제외
- `learning_ref_b57d6e449743` rejected -> shortlist | tags: - | 빠른 비교에서 둘 다 참고 후보
- `learning_ref_b8e9732e811e` rejected -> shortlist | tags: - | 빠른 비교에서 둘 다 참고 후보
- `learning_ref_c02552919599` shortlist -> selected | tags: - | 빠른 비교에서 더 적합한 레퍼런스로 선택
- `learning_ref_c05cd1b4c7b3` shortlist -> rejected | tags: - | 빠른 비교에서 상대적으로 부적합
- `learning_ref_c3b8e940ef78` shortlist -> shortlist | tags: - | 빠른 비교에서 둘 다 참고 후보
- `learning_ref_c6dcd9b6263b` shortlist -> shortlist | tags: - | 빠른 비교에서 둘 다 참고 후보
- `learning_ref_c9929f77dd67` shortlist -> rejected | tags: - | 빠른 비교에서 상대적으로 부적합
- `learning_ref_cd15008c6489` rejected -> selected | tags: - | 빠른 비교에서 더 적합한 레퍼런스로 선택
