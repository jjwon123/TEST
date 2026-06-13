# Reference Session Comparison - cosmetics_skincare

| Session | Reviewed | Accuracy | AI decisions | Final decisions | Main transitions |
|---|---:|---:|---|---|---|
| `pinterest_holdout_001` | 47/47 | 0.468 | {'selected': 0, 'shortlist': 23, 'rejected': 24} | {'selected': 14, 'shortlist': 20, 'rejected': 13} | rejected->shortlist:9, shortlist->shortlist:11, rejected->rejected:11, shortlist->selected:10, rejected->selected:4, shortlist->rejected:2 |
| `pinterest_holdout_002` | 36/36 | 0.528 | {'selected': 2, 'shortlist': 21, 'rejected': 13} | {'selected': 2, 'shortlist': 31, 'rejected': 3} | selected->shortlist:1, shortlist->shortlist:19, rejected->selected:2, selected->rejected:1, rejected->shortlist:11, shortlist->rejected:2 |
| `pinterest_holdout_003` | 0/31 | pending | {'selected': 2, 'shortlist': 17, 'rejected': 12} | {'selected': 0, 'shortlist': 0, 'rejected': 0} | - |
| `pinterest_session_001` | 100/100 | 0.15 | {'selected': 41, 'shortlist': 56, 'rejected': 3} | {'selected': 29, 'shortlist': 12, 'rejected': 59} | selected->rejected:26, shortlist->rejected:32, rejected->shortlist:1, selected->shortlist:6, rejected->selected:1, shortlist->selected:19, rejected->rejected:1, selected->selected:9, shortlist->shortlist:5 |
