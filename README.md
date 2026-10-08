# 朽ち神楽 / KUCHI KAGURA

日本の因習村を舞台にした、ブラウザで遊べる一人称探索ホラーです。
村の屋敷・井戸・蔵で三枚の鎮め札を集め、北の社で境の鍵を受け取り、南の門から脱出します。
オリジナルの女性型追跡怪異「朽ち神楽」、Blender編集用モデル、8種類の骨格アニメーションも含みます。

## ゲームを起動する

Windowsでは `PLAY.bat` を実行します。既存の `PREVIEW_ONLY.bat` でもゲーム本編が開きます。
リポジトリから取得した場合、最初にNode.jsを用意して `npm ci` を実行してください。
Linuxでは `npm ci` のあと `npm start` を実行します。標準ポートは8765です。
HTTPサーバーが必要なので、`web/index.html` を直接ダブルクリックして開く方法には対応していません。
ゲーム本編は `/`、元の8動作プレビューは `/character.html` です。
`npm run build:web` は依存ファイルを同梱した静的サイトを `dist/` に生成します。
`dist/` はHTTPサーバーのルートでもサブディレクトリでも配信できます。

### GitHub から取得・公開する

ソースと編集用モデルは [porco810/horror-game](https://github.com/porco810/horror-game) の `main` ブランチです。
GitHub の「Code → Download ZIP」で取得し、展開したフォルダーで `npm ci` を実行してください。
Three.jsを同梱した完成版ZIPは [KUCHI_KAGURA_GAME_V1.zip](https://github.com/porco810/horror-game/raw/refs/heads/gh-pages/downloads/KUCHI_KAGURA_GAME_V1.zip) です。

`gh-pages` ブランチには依存ファイルを同梱した静的サイトを配置します。
GitHub の [Settings → Pages](https://github.com/porco810/horror-game/settings/pages) で、
Sourceを「Deploy from a branch」、Branchを「gh-pages / (root)」にして保存すると公開できます。
公開設定とGitHub側の配信処理が完了したあとのゲームURLは `https://porco810.github.io/horror-game/`、
キャラクター確認は `https://porco810.github.io/horror-game/character.html` です。
URLを記載しただけでは公開の完了を意味しません。GitHub側のPages設定と実際の表示を確認してください。

### 操作

| 操作 | キー |
| --- | --- |
| 移動・見回す | WASD・マウス。ドラッグと矢印キーも対応 |
| 走る・しゃがむ | Shift・C。Ctrlは押している間だけしゃがむ |
| 調べる・拾う | E |
| 懐中電灯 | F |
| 所持品を選ぶ | 1〜6・画面下の所持品 |
| 投げる・鈴を鳴らす | G。マウス視点固定中は左クリックでも投げる |
| 神楽鈴 | R。再使用まで12秒、消耗しない |
| 手記・見取り図 | Tab |
| 一時停止 | Esc・P |

スマートフォンでは左の移動パッド、右側のドラッグ、調べる・手向けるボタンを使います。
写真・かんざし・子どもの草履に反応すると嘆き、握り飯・団子なら食らい、鈴なら神楽を舞います。
品物は怪異の近くへ投げてください。気づかれなかった品物は地面に残り、Eで拾い直せます。
走る音や灯りに気づかれたら、家の陰に隠れて視線を切り、灯りを消してしゃがみましょう。
設定から追跡を「穏やか」にし、明るさ・音量・視点感度・揺れ・描画品質を調整できます。

拾得・手向け・祭壇の進行をブラウザのlocalStorageに自動保存します。
「記憶の続きから」や捕獲後の再開では、入口または社の安全な場所へ戻ります。
ブラウザの保存を禁止している場合は、この画面を閉じるまでメモリーに保持します。
環境やポート・ブラウザを変えるとセーブは共有されません。新規開始では既存のセーブを置き換えます。

<details><summary>結末の条件（ネタバレ）</summary>

通常の脱出に加え、写真・かんざし・草履の三つすべてを怪異に手向けてから脱出すると、別の結末になります。

</details>

ゲーム構成と実装の境界は `GAME_DESIGN.md` を参照してください。

## 生成物

- `export/kuchikagura_game.blend` — 材質・1Kアトラス・骨格・8アクションを保持する編集用ファイル。
- `web/assets/models/kuchikagura.glb` — 27,904 triangle、20ボーン、8アニメーション、埋め込みテクスチャ1枚。
- `export/textures/kuchikagura_atlas_1k.png` — 1024×1024の衣装・髪・肌・植物アトラス。
- `export/build_report.json` — 実際の生成環境とアセット数値。
- `export/asset_validation.json` / `export/gltf_validation.json` — バイナリ・骨格・アニメーション・glTF形式の検証。

生成物は再生成のためのキャッシュではなく、ゲームに取り込める納品物として残しています。
主人公モデルは含みません。POV用両腕は `pov_arms.glb` という独立アセットをカメラに追加する設計です。
村マップは手続き生成したオリジナルの建物・石畳・杉林・灯籠・社で構成し、衝突判定と経路探索を持ちます。

## クラウド / Linux

検証済み環境: Blender 4.3.2、Python 3.12、Node.js 24、Three.js 0.180.0、Chromium。
Blender内のPythonにはモデル生成用のNumPyが付属しています。Python仮想環境へのbpyインストールは不要です。

```bash
cd /workspace/horror-game
npm ci --include=dev --ignore-scripts --no-audit --no-fund --cache /workspace/scratch/npm-cache
npm run build
npm run validate
npm run test:logic
npm run preview
```

別ターミナルで `npm run test:game`（本編）と `npm run test:browser`（キャラクター確認）を実行できます。
`npm run build:web` のあと `npm run test:static` で、別のHTTPサーバーのサブディレクトリでも読み込みと操作を確認できます。
ブラウザ検証はPython Playwrightと `/usr/bin/chromium` を使います。このクラウドには両方が入っています。
サーバーの標準ポートは8765です。必要なら `KUCHI_PREVIEW_PORT` で変更し、検証時にも同じ値を指定してください。
Web表示に外部CDN、APIキー、認証情報は必要ありません。依存更新時だけ `registry.npmjs.org` を使います。

## Windows

`PLAY.bat` または `PREVIEW_ONLY.bat` を実行すると、生成済みモデルを使ったゲーム本編が開きます。
完成版ZIPにはWeb表示に必要なThree.jsの公式ファイルとライセンスも同梱しています。
`BUILD_AND_PREVIEW.bat` はモデルを再生成してプレビューを開きます。
バッチはご指定の `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe` を最初に探します。
Gitリポジトリから取得した場合はNode.jsをインストールし、最初に `npm ci` を実行してください。

このクラウドはLinuxなのでWindowsバッチとBlender 5.2.2での実行は未検証です。
生成スクリプトは旧アクションと新しいレイヤー付きアクションの両方を扱います。
エラー時は `build_log.txt` と `build_python_error.txt` に詳細が残り、処理は失敗を返します。

## ゲームへ組み込む

WebページでThree.jsとadd-onsのimport mapを設定し、`character-controller.js` を読み込みます。
このGLBはスキンメッシュと骨格を含むため、移動・回転は `controller.model` 全体に適用してください。
単位はメートル、上方向+Y、正面+Z。歩行・追跡はin-placeで、位置更新・ナビゲーション・衝突処理はゲーム側で行います。

```js
import {KuchikaguraController} from './character-controller.js';
const pursuer = await KuchikaguraController.load('./assets/models/kuchikagura.glb');
scene.add(pursuer.model);
pursuer.model.position.set(0, 0, -5);
pursuer.play('walk');
// 写真・かんざし・子どもの草履 → lament、おにぎり・団子 → feed、神楽鈴 → ritual。
pursuer.reactToItem('photograph');
// ゲーム自身の拾得アイテムを表示する場合はデモ小道具を隠す。
pursuer.showReactionProps = false;
// 毎フレーム、経過秒を渡す。onceの終了後はidleへ戻る。
pursuer.update(deltaSeconds);
```

カメラ用両腕は追跡者とは別のGLB・AnimationMixer・読み込み処理で管理します。
`web/assets/models/manifest.json` に後から追加するアセットの境界を記しています。

## プレビューと検証

8つの動作ボタン、6種類の投げる品物、停止・時刻指定・速度変更、霧・回転・照明切り替えを備えています。
写真・食べ物・鈴の反応は実際のGLBの骨格アニメーションを再生します。
`npm run validate` は三角形数、正規化されたウェイト、全クリップの実データ、ループ境界、1K埋め込み画像を検査し、
Khronos glTF Validatorで形式を検証します。`npm run test:browser` は8動作の骨格変化・描画、6品目、再生操作、モバイル表示を検証します。
スクリーンショットとブラウザ結果は `export/verification/` に保存します。

`npm run test:logic` は移動の壁抜け防止、遮蔽・経路探索、追跡・捜索・反応、保存復元を検証します。
`npm run test:game` は実際のブラウザ上で操作、全拾得、投擲・拾い直し、保存・再読み込み、各反応、
捕獲と再開、祭壇と鍵、二つの結末、スマートフォンの実タッチ入力まで検証します。
テストでは移動区間を短縮するために `?test=1` の専用APIと固定刻みを使います。通常のページではこのAPIを公開しません。
通常ページのフレーム更新による入力も別に検査します。結果は `export/game-verification/game_validation.json` に保存します。
音はWeb Audioによる独自の環境音・足音・鈴・鼓動です。自動検証は音の主観的な聞こえ方まで保証しません。

材質・髪・衣装のディテールは手続き生成したオリジナルです。既存作品のキャラクターや外部画像は使っていません。
Three.jsとglTF Validatorのライセンスはそれぞれのnpmパッケージに従います。
