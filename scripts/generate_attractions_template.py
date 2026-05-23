"""TDL アトラクションマスタの雛形生成スクリプト（**retired**）。

このスクリプトは Phase 3 の初期マスタ構築時に使用された雛形生成器。
その後 data/attractions.json には以下が手動で投入され、スクリプト内の
ATTRACTIONS テーブルとは大きく乖離した:

- lat / lng（Phase 3 で東郷さん人力入力）
- queue_times_id / avg_wait_min（5/22 Queue-Times 切替時）
- pass_type の正確な分類（5/23 pass_type refactor: pooh / monsters_inc を
  priority に訂正、big_thunder / haunted_mansion / star_tours を priority 新規追加、
  splash_mountain を dpa 新規追加、buzz を削除）
- baymax の requires_reservation: true 昇格

以降、attractions.json は手書きで保守する運用に切り替えた。
このスクリプトを再実行すると上記の蓄積が全消去されるため、retired。
歴史的経緯はこの docstring とコミット履歴で辿れる。
"""
from __future__ import annotations

import sys


def main() -> None:
    sys.exit(
        "❌ このスクリプトは retired です。data/attractions.json は手書きで保守してください。\n"
        "   経緯は scripts/generate_attractions_template.py 冒頭の docstring 参照。"
    )


if __name__ == "__main__":
    main()
