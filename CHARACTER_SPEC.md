# 朽ち神楽 — ゲーム用キャラクター

日本の因習村に残された祭祀の記憶が人の輪郭を取った、オリジナルの女性型追跡怪異。
長い黒髪、古い白い祭祀衣装、褪せた赤い袴、長めの腕、不自然な首の傾き、
折り紙状の紙垂、藁縄、蔓と淡い花の侵食を持つ。露骨なグロ表現は含めない。

1つのスキンメッシュ、20ボーン、27,904 triangle、1枚の1024×1024埋め込みアトラス。
Blenderの材質別プリミティブは8つ。GLBの単位はメートル、上方向+Y、正面+Z。
全アニメーションは30fpsでサンプルしたin-place動作。移動量はゲーム側で制御する。

| Clip | 秒 | 再生 | 用途 |
| --- | ---: | --- | --- |
| idle | 3.6 | loop | 呼吸、静かな揺れ、首の傾き |
| walk | 1.2 | loop | 左右の脚・腕を使った巡回 |
| alert | 2.4 | once | 立ち止まり、音の方向を見る |
| chase | 0.8 | loop | 前傾姿勢の追跡 |
| search | 4.8 | loop | 周囲を見回し、手を伸ばして探す |
| lament | 7.2 | once | 拾う、見つめる、しゃがむ、震えながら嘆く |
| feed | 5.2 | once | 急いで拾う、食べ物を口に運ぶ、乱暴に食らう |
| ritual | 5.6 | loop | 立ち止まり、両腕を広げて不自然な神楽 |

思い出の品は photograph / hairpin / child_sandals、食べ物は onigiri / dango、鈴は kagura_bell。
写真・おにぎり・鈴は反応デモ用小道具を骨に付けて表示する。
実ゲームで独自の品物を表示する場合はコントローラーの showReactionProps=false を設定できる。

骨格: ROOT_CTRL / HIPS_CTRL / TORSO_CTRL / NECK_CTRL / HEAD_CTRL、
左右の ARM / ELBOW / HAND / THIGH / SHIN / FOOT 各CTRL、
MEMORY_PROP_CTRL / FOOD_PROP_CTRL / BELL_PROP_CTRL。

長髪の下端は頭と胴のブレンドウェイトで曲がる。布・髪の物理シミュレーションは焼き込まない。
移動、経路探索、当たり判定、投擲物の物理挙動はゲーム側の役割。
POV用両腕は別GLBをカメラに親子付けし、この骨格や追跡者モデルから独立させる。
