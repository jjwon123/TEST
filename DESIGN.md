---
name: LoopStudio Production Console
source: oh-my-design / Nexon
source_path: .tmp/oh-my-design/design-md/nexon/DESIGN.md
adaptation: workflow-first content production console
---

# LoopStudio Design System

LoopStudio는 이벤트 브리프부터 콘셉트, 카피, 이미지, QA까지 이어지는 제작 도구다. 화면은 게임 UI를 흉내 내지 않고, 사용자가 지금 해야 할 한 가지 작업과 다음에 열릴 단계를 분명히 보여주는 "성숙한 미션 보드"로 설계한다.

## Visual foundation

- Canvas: `#ffffff`
- Primary ink: `#17191d`
- Body text: `#737881`
- Label text: `#4a4e57`
- Muted text: `#919191`
- Disabled: `#9fa1a7`
- Borders: `#e6e8eb`; strong border `#cfd3d8`
- Brand action: `#00de5a` with `#17191d` text
- Warning and error colors are semantic only. Recommendation is never gold.
- Green appears at most twice in a viewport: the primary action and one active-progress marker.

## Typography

- Headings and primary actions: `NEXON Gothic Bold`, falling back to `Pretendard`, `Malgun Gothic`, sans-serif.
- Body: `Malgun Gothic`, `Pretendard`, sans-serif.
- Use large, direct Korean labels. Avoid decorative all-caps except short eyebrows.

## Shape and depth

- Primary CTA: square corners (`0px`).
- Cards and controls: `4px` radius.
- Large workspace containers: `8px` radius.
- Use neutral, functional shadows only: `0 2px 8px rgba(23,25,29,.06)`.
- Do not use pill-shaped navigation, cards, filters, or status decoration. A compact status tag may use `2px` radius.

## Spacing

Use an 8px base system: `8, 16, 24, 32, 40, 48`. Dense review content may use 12px gaps, but page-level composition remains calm and generous.

## Product structure

1. The horizontal production journey is visible before task content.
2. The center workspace presents exactly one current mission.
3. Options are compact comparison cards with the same information order.
4. The right inspector explains evidence, risk, and provenance for the selected option.
5. A sticky action bar states what completion unlocks and offers one primary action.
6. Deep diagnostics, audit tables, and batch controls stay available under a secondary disclosure.

## Gamification

- Use completion, current, and locked states only.
- Completed steps use ink and a simple check label; the current step uses a single green marker.
- Never use XP, ranks, coins, streaks, treasure, celebratory gradients, or reward colors.
- The reward is operational clarity: "완료하면 카피 단계가 열립니다."

## Components

### Production journey

Six chapters: 브리프 → 콘셉트 → 카피 → 이미지 방향 → 이미지 선택 → QA·보관. Completed chapters are dark, the current chapter has the sole progress-green marker, and future chapters are gray.

### Mission card

The mission header contains a small chapter label, a plain-language title, a one-sentence instruction, and optional neutral status. It must never compete with the primary action.

### Concept card

Show name, axis, target insight, core promise, and expected role. Selected state uses a 2px `#17191d` border. Recommended state uses a neutral text label, not a colored highlight.

### Evidence inspector

Show the selected concept's primary insight first, then numbered source/evidence rows, then one risk note. Provenance should be readable without opening developer data.

### Action bar

Sticky at the bottom of the mission workspace. Secondary actions are white with neutral borders. The one primary button is `#00de5a`, black text, square corners.

## Do / don't

- Do lead with the next human decision.
- Do preserve full audit tools behind progressive disclosure.
- Do keep comparison fields aligned across cards.
- Don't show global metrics before the current mission.
- Don't repeat green across completed states, badges, nav, and cards.
- Don't use rounded-pastel dashboard cards as the main visual language.
- Don't expose raw pipeline terminology when a plain Korean action label exists.
