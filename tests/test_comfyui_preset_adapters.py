from __future__ import annotations

import unittest

from services.comfyui.preset_adapters import build_api_prompt


class ComfyUIPresetAdapterTests(unittest.TestCase):
    def test_korean_overlay_defaults_remove_ratio_badge_and_raise_contrast(self) -> None:
        prompt = build_api_prompt("korean_poster_overlay_1024", {
            "base_image": "base.png",
            "ratio": "4:5",
            "headline": "제품의 기준을 다시 쓰다",
            "subheadline": "매일의 선택을 더 선명하게",
        })

        self.assertEqual("", prompt["3"]["inputs"]["text"])
        self.assertEqual("#17324D", prompt["4"]["inputs"]["text_color"])
        self.assertEqual("C:/Windows/Fonts/malgunbd.ttf", prompt["4"]["inputs"]["font_path"])
        self.assertEqual(0, prompt["4"]["inputs"]["stroke_width"])
        self.assertGreaterEqual(prompt["4"]["inputs"]["box_width"], 790)

    def test_korean_overlay_allows_explicit_badge_and_colors(self) -> None:
        prompt = build_api_prompt("korean_poster_overlay_1024", {
            "base_image": "base.png",
            "badge": "NEW",
            "text_color": "#FFFFFF",
            "secondary_text_color": "#EEEEEE",
            "footer_text_color": "#DDDDDD",
        })

        self.assertEqual("NEW", prompt["3"]["inputs"]["text"])
        self.assertEqual("#FFFFFF", prompt["4"]["inputs"]["text_color"])
        self.assertEqual("#EEEEEE", prompt["5"]["inputs"]["text_color"])
        self.assertEqual("#DDDDDD", prompt["6"]["inputs"]["text_color"])

    def test_product_locked_prompt_documents_visible_product_scale(self) -> None:
        prompt = build_api_prompt("product_locked_ad_background_v1", {
            "product_image": "product.png",
            "ratio": "4:5",
        })

        self.assertEqual("ProductLockedAdComposite", prompt["2"]["class_type"])
        self.assertEqual(0.58, prompt["2"]["inputs"]["product_scale"])


if __name__ == "__main__":
    unittest.main()
