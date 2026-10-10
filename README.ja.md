# oncemore

*The DVD authoring app Mac forgot. Menus, chapters, ISO — once more.*

[English README](README.md)

oncemore は、動画ファイルから **メニュー付きの DVD-Video ディスクイメージ** を作るツールです。
ボタン付きの静止メニュー、サムネイル付きチャプターメニューの自動生成、チャプタージャンプ、
「本編が終わったらメニューに戻る」を、JSON ファイル 1 つで記述して `.iso` を書き出します。
できた ISO は VLC で再生・マウント・書き込みができます。

**自分の Mac 上でブラウザから使うオーサリングアプリ**（`oncemore gui`）として動き、
その下にスクリプトからも使えるコマンドライン版があります。アプリは手元のマシンから配信され、
ファイルはどこにもアップロードされません。

![メニューエディタ](docs/images/gui-menu-ja.png)

## 背景

Adobe Encore は 2012 年に開発終了、Apple の DVD Studio Pro と iDVD も無くなり、
Final Cut Pro 10.8 ではディスク書き出し自体が削除されました。DVDStyler の macOS 版は
Intel ビルドのままです。一方、DVD-Video の必須コーデックは特許が切れており
（MPEG-2 は 2018 年、AC-3 は 2017 年）、オープンソースで正面から実装できます。
コピーガードは実装しません（今後も入れません）。

## インストール

oncemore 本体は Python 3.11+ の標準ライブラリのみで動きます。外部プログラムを呼び出します：

| プログラム | 用途 |
|---|---|
| `ffmpeg` / `ffprobe`（`drawtext` フィルタ入り） | MPEG-2/AC-3 エンコード、メニュー描画、解析 |
| `dvdauthor` / `spumux` | DVD-Video 構造（IFO/VOB）、ボタンのハイライト |
| **UDF** を書ける ISO ツール：`hdiutil`（macOS 標準）、`genisoimage`、`mkisofs` | ディスクイメージ |

### macOS（Homebrew）

```sh
brew install ffmpeg-full dvdauthor
pip install git+https://github.com/kajisho5/oncemore
oncemore doctor
```

* `ffmpeg` ではなく **`ffmpeg-full`** を入れてください。Homebrew の `ffmpeg` は
  libfreetype なしでビルドされており、メニュー文字に使う `drawtext` フィルタがありません。
  `ffmpeg-full` は keg-only（PATH にリンクされない）ですが、oncemore が
  `$(brew --prefix)/opt/ffmpeg-full/bin` を自動で探します。
* ISO は macOS 標準の `hdiutil`（UDF 1.02 + ISO 9660）で作るので、追加の ISO ツールは不要です。
  代替として `brew install cdrtools` で `mkisofs` も使えます。

### Debian / Ubuntu

```sh
sudo apt-get install ffmpeg dvdauthor genisoimage
pip install git+https://github.com/kajisho5/oncemore
oncemore doctor
```

インストールせずにチェックアウトから `python -m oncemore ...` でも実行できます。

ツールの場所は `ONCEMORE_FFMPEG`、`ONCEMORE_FFPROBE`、`ONCEMORE_DVDAUTHOR`、
`ONCEMORE_SPUMUX`、`ONCEMORE_GENISOIMAGE`、`ONCEMORE_MKISOFS`、`ONCEMORE_XORRISO`、
メニューのフォントは `ONCEMORE_FONT` で上書きできます。
足りないツールがあれば、何が無いかとインストールコマンドを表示して終了します。

## Mac アプリ

**Oncemore.app** は同じ編集画面を普通の Mac のウィンドウで開くアプリです。ダブルクリックで起動し、
「File › New Project… / Open Project…」でプロジェクトを作成・オープン、次回は前回のプロジェクトを自動で開きます。
Python は同梱しているので、Homebrew で入れるのは映像ツールだけです：

```sh
brew install ffmpeg-full dvdauthor
```

[Releases](https://github.com/kajisho5/oncemore/releases) ページ（または最新の CI 実行の成果物）から
`Oncemore-<version>-arm64.zip`（Apple シリコン用）か `Oncemore-<version>-x86_64.zip`（Intel 用）を
ダウンロードして展開し、*Oncemore.app* を「アプリケーション」に入れてください。まだ公証（notarize）していないため、
初回起動は macOS にブロックされます。「システム設定 › プライバシーとセキュリティ」で **このまま開く** を押すか、
`xattr -dr com.apple.quarantine /Applications/Oncemore.app` を実行してください。
自分でビルドする場合は `macos/build_app.sh`（Xcode コマンドラインツールと `gh` が必要）。Developer ID があれば
`CODESIGN_IDENTITY` と `NOTARIZE=1` で署名・公証済みのアプリを作れます。
タグ `v<version>` を push すると `.github/workflows/release.yml` が両アーキテクチャをビルドし、
それぞれサンプルプロジェクトで起動確認したうえで zip を下書きリリースに添付します
（ファイル冒頭に書いた署名用 secrets を設定すれば署名・公証済みになります）。

## クイックスタート：ブラウザでアプリ

```sh
oncemore gui my-disc          # ブラウザで http://127.0.0.1:…/ が開きます
```

* **新しいプロジェクト** →「サンプル付きで作成」で動く見本ディスクを確認できます。
  空で始めた場合は、**動画ファイルをウィンドウにドロップ**します。
* **タイトル**：「素材」で動画を選び「タイトルとして追加」。スクラブして、チャプターを切りたい位置で
  **◆ ここにチャプター**。「サムネイル付きチャプターメニューを自動生成」にチェックするとチャプターメニューができます。
  再生終了後の動作・音声トラック・字幕（`.srt`）は右のパネルで設定します。
* **メニュー**：「＋追加」して、ボタンやテキストをドラッグで配置。各ボタンのリンク先
  （メニュー・タイトル・チャプター・音声/字幕の切替）を選びます。背景には画像か動画を使えます。
  **実レンダリング確認**で、ディスクで実際に表示される見た目とボタンの当たり判定を確認できます。
* **チェック**で容量の見積もりと問題点の確認、**書き出し**で `my-disc/output/` に
  `.iso`（または VIDEO_TS フォルダ）を進捗表示付きで書き出します。
* 編集は `my-disc/project.oncemore.json` に自動保存され、⌘Z / Ctrl+Z で元に戻せます。
  表示言語はブラウザに合わせて英語/日本語（文A ボタンで切替）。

![タイムライン上のチャプター](docs/images/gui-title-ja.png)

アプリは 127.0.0.1 でのみ待ち受け、起動ごとのランダムなキーを URL に含めます。
読み書きするのはプロジェクトフォルダ内のファイルだけです。

## クイックスタート：コマンドライン

```sh
oncemore init demo                                   # サンプルプロジェクト＋テスト素材を生成
oncemore preview-menu demo --menu main -o main.png   # メニューの見た目を確認
oncemore iso demo/project.oncemore.json -o demo.iso  # エンコード→オーサリング→ISO
```

サンプルには、メインメニュー（PLAY ALL / CHAPTERS / SAMPLE TITLE B）、サムネイル付きの
自動チャプターメニュー、3 チャプターの 16:9 タイトル、4:3 のタイトル（ピラーボックス）が
入っています。素材はすべて ffmpeg のテストソースで生成するので、リポジトリに大きな
バイナリは含みません。

## コマンド

```
oncemore init <dir> [--standard NTSC|PAL] [--aspect 16:9|4:3] [--force]
oncemore validate <project> [--no-media]       # スキーマ＋参照＋素材＋容量見積もり
oncemore build <project> -o out/               # out/VIDEO_TS（と out/AUDIO_TS）を生成
oncemore iso <project> -o out.iso [--iso-tool auto|hdiutil|genisoimage|mkisofs|xorriso]
oncemore preview-menu <project> --menu main -o main.png [--button id] [--state highlight|select|normal] [--outline]
oncemore gui [<dir>] [--port N] [--no-browser] # オーサリングアプリ
oncemore doctor                                # 外部ツールの有無・バージョン・ISO バックエンド
```

* `<project>` は `project.oncemore.json` かそれを含むディレクトリ。
* `build` / `iso` は既定で **2 パス**エンコード。`--fast` で 1 パス。
* 中間ファイルは `out/.work/`（`iso` では ISO の隣の隠しビルドディレクトリ）に置き、
  `--keep-work` が無ければ成功時に削除します。各外部コマンドのログは `.work/logs/`。
* `--json`（コマンドの前後どちらでも可）で stdout が **JSON Lines** になります（GUI 連携用）：
  `step`、`progress`（`fraction` 0〜1）、`log`、最後に `result` か `error`。
  終了コード：0 成功、1 エラー、2 プロジェクト不正、3 ツール不足、4 外部ツール失敗。

## プロジェクトファイル

入力は `project.oncemore.json` だけです。JSON Schema：
[schema/project.schema.json](schema/project.schema.json)。パスはプロジェクトファイルからの
相対パス。例：[examples/basic/project.oncemore.json](examples/basic/project.oncemore.json)。

```jsonc
{
  "version": 1,
  "disc": {
    "label": "SAMPLE_DISC",      // ボリュームラベル。A-Z 0-9 _ の 32 字以内に正規化
    "standard": "NTSC",          // NTSC（720x480, 29.97）| PAL（720x576, 25）
    "aspect": "16:9",            // 4:3 | 16:9
    "target": "DVD5",            // DVD5（4.37 GiB）| DVD9（7.95 GiB）
    "first_play": "menu:main",   // menu:<id> | title:<id>。既定は最初のメニュー
    "font": null,                // メニュー文字のフォント。null で自動検出
    "video_bitrate": "auto"      // "auto" で容量に合わせて自動。固定なら "6M" など
  },
  "titles": [
    {
      "id": "t1",
      "name": "Sample Title A",                     // チャプターメニューの見出し
      "source": "media/sample_a.mp4",
      "chapters": ["00:00:00", "00:00:08", 16],     // "HH:MM:SS[.ms]"、"MM:SS"、秒数
      "audio": { "codec": "ac3", "bitrate": "192k" },// ac3 | lpcm（48kHz/16bit）
      "end_action": "title:t2",                     // menu:<id> | title:<id> | stop
      "auto_chapter_menu": { "id": "chapters", "back": "menu:main" }  // または true
    }
  ],
  "menus": [
    {
      "id": "main",
      "background": "media/menu_bg.png",   // 静止画。null なら background_color
      "audio": null,                       // 任意。ループ BGM
      "texts": [{ "text": "SAMPLE DISC", "x": 120, "y": 90, "size": 56 }],
      "buttons": [
        { "id": "play", "label": "PLAY ALL", "x": 120, "y": 220, "action": "title:t1" },
        { "id": "ch",   "label": "CHAPTERS", "x": 120, "y": 280, "action": "menu:chapters" }
      ],
      "highlight_color": "#FFD400",
      "select_color": "#FF5A00"
    }
  ]
}
```

### リファレンス

**disc**

| キー | 型・値 | 既定値 |
|---|---|---|
| `label` | 文字列 → A–Z 0–9 `_`、32 字以内 | 必須 |
| `standard` | `NTSC` \| `PAL` | 必須 |
| `aspect` | `4:3` \| `16:9` | 必須 |
| `target` | `DVD5` \| `DVD9` | `DVD5` |
| `first_play` | `menu:<id>` \| `title:<id>` | 最初のメニュー、無ければ最初のタイトル |
| `font` | パス または `null` | 自動：ヒラギノ（macOS）→ Noto Sans CJK → DejaVu Sans |
| `video_bitrate` | `"auto"` かビットレート（`"6M"`、`5500000`）、1〜8 Mbps | `auto` |
| `subtitle_style` | 全字幕の `{size, color, outline, outline_width, margin}` | 30px（PAL 36）、白、黒縁 3px、下から 36px（PAL 43） |

**titles[]**（1〜99）

| キー | 型・値 | 既定値 |
|---|---|---|
| `id` | `[A-Za-z0-9_-]{1,40}` | 必須 |
| `name` | 文字列 | id |
| `source` | ffmpeg が読める動画 | 必須 |
| `chapters` | 時刻のリスト。0 が無ければ自動追加 | `[0]` |
| `audio.codec` | `ac3` \| `lpcm` | `ac3` |
| `audio.bitrate` | AC-3 のみ、64k〜448k | `192k` |
| `end_action` | `menu:<id>` \| `title:<id>` \| `stop` | first_play のメニュー、無ければ `stop` |
| `aspect` | このタイトルの `4:3` \| `16:9` | `disc.aspect` |
| `audio.lang` | 音声（1 トラック時）の ISO 639-1 言語コード | なし |
| `audio_tracks` | 1〜8 個の `{source?, stream?, lang?}`：複数音声（下記） | `source` の音声 1 本 |
| `subtitles` | 32 個までの `{file, lang?, default?}` SRT ファイル（下記） | なし |
| `auto_chapter_menu` | `true` またはオブジェクト（下記） | なし |

`auto_chapter_menu` のオブジェクト：`id`（既定 `chapters_<タイトルid>`、2 ページ目以降は
`_2`、`_3`…）、`title`（見出し）、`back`（BACK ボタンのアクション。既定は first_play のメニュー）、
`label_format`（既定 `"Chapter {n}"`）、`back_label`、`prev_label`、`next_label`、
`background`、`background_color`、`text_color`、`highlight_color`、`select_color`、
`audio`、`duration`。1 ページ 6 チャプターで、超えると PREV/NEXT ボタンが付きます。

**menus[]**（99 以内）

| キー | 型・値 | 既定値 |
|---|---|---|
| `id` | 識別子 | 必須 |
| `background` | 静止画 または `null` | `null` |
| `background_color` | `#RRGGBB` | `#000000` |
| `background_video` | **モーションメニュー**用の動画（`background` より優先） | `null` |
| `audio` | 音楽ファイル または `null` | 背景動画の音、無ければ無音 |
| `duration` | ループの長さ（秒） | 動画／BGM の長さ（600 以下）、無ければ 5 |
| `font_size`、`text_color` | テキスト・ボタンの既定値 | `32`、`#FFFFFF` |
| `highlight_color`、`select_color` | ボタンの色 | `#FFD400`、`#FF5A00` |
| `texts[]` | `{text, x, y, size?, color?}` 装飾テキスト | `[]` |
| `buttons[]` | 1〜36 個 | 必須 |

**buttons[]**：`id`、`label`、`x`、`y`（ラベルの左上）、`action`
（`menu:<id>` \| `title:<id>` \| `chapter:<タイトルid>:<番号>` \| `audio:<n>` \|
`subtitle:<n>` \| `subtitle:off` \| `stop`）、任意で `size`、`color`、自動ナビゲーションを
上書きする `nav`（`{"up": id, "down": id, "left": id, "right": id}`）。
`audio:<n>` / `subtitle:<n>`（1 始まり）はストリームを切り替えてメニューに留まるので、
「音声・字幕設定」メニューはこれらのボタンと BACK ボタンを並べるだけで作れます。

### 複数音声と字幕

```jsonc
"titles": [{
  "id": "t1", "source": "media/movie.mp4",
  "audio": { "codec": "ac3", "bitrate": "192k" },          // 全トラック共通
  "audio_tracks": [
    { "lang": "ja" },                                       // source の音声ストリーム 0
    { "source": "media/commentary.wav", "lang": "en" },     // 別ファイル
    { "stream": 1, "lang": "fr" }                           // source の 2 本目の音声
  ],
  "subtitles": [
    { "file": "media/ja.srt", "lang": "ja", "default": true },
    { "file": "media/en.srt", "lang": "en" }
  ]
}]
```

* 各トラックは映像の長さに合わせて無音で埋める／切り詰めます。存在しないストリームは `validate` が報告します。
* DVD はストリーム属性を titleset 単位で持つため、n 番目のストリームの言語はディスク全体で 1 つです
  （タイトル間で `lang` を揃える必要があります）。
* 字幕は SubRip（`.srt`、UTF-8 または Shift_JIS）。各字幕をメニューと同じフォントで
  （白文字＋縁取り、`disc.subtitle_style` で変更可）描き、DVD の 4 色サブピクチャに減色して
  spumux で多重化します。`<i>` や `{\an8}` などの装飾タグは除去し、時間が重なる字幕は前を短くします。
* `"default": true` の字幕はディスク起動時に表示 ON になります（その後の視聴者の選択は保持）。
  指定が無ければ字幕は OFF で始まります。

**座標** はアスペクト比に関係なく DVD のピクセル（NTSC 720×480、PAL 720×576）です。
文字は正方ピクセルのキャンバスに描いてから圧縮するので、16:9 でも横に伸びません。
ボタンの当たり判定はラベルが実際に描かれた範囲から算出し、上下左右の移動先は
ボタンの位置から自動計算します（行・列内で端から反対側へ回り込みます）。

## 仕組み

```
素材 ─ffprobe─▶ ビットレート計画 ─ffmpeg（2パス MPEG-2 + AC-3/LPCM）─▶ titles/*.mpg
メニュー JSON ─ffmpeg drawtext─▶ base.png ─▶ menu.mpg ─spumux（4色 PNG ハイライト）─▶ menu.mpg
dvdauthor XML ─dvdauthor─▶ VIDEO_TS ─hdiutil / genisoimage─▶ disc.iso
```

* **ビットレート**：全タイトルの尺、音声ビットレート、メニュー分と 2% の余裕から算出し、
  映像 8 Mbps・合計 9.8 Mbps を上限にします。
* **映像**：720×480/576 にスケーリング＋レターボックス／ピラーボックス、29.97/25fps に変換、
  DAR は 4:3/16:9 のフラグ、色は BT.601。
* **チャプター**はフレーム精度です。チャプター位置にキーフレームを強制し、その直前の GOP 長を
  計画して各チャプターが独立した VOBU から始まるようにしています（DVD は VOBU を 0.4 秒以上と
  定めており、短い GOP は dvdauthor が併合してチャプターが最大 0.5 秒ほど前にずれるため）。
* **メニュー**はすべて 1 つの titleset に置き、ボタンからはメニュー・タイトル・チャプターへ直接ジャンプします。
  タイトルからはその titleset のルートメニューしか呼べないため、別のメニューへ戻るときは
  GPRM `g1` に行き先番号を入れてルートメニュー経由で振り分けます。
* **titleset**：DVD は映像・音声の形式を titleset 単位で持つため、タイトルを（アスペクト比, 音声コーデック）で
  自動的にグループ分けします。16:9 AC-3 のタイトルに 4:3 LPCM のタイトルを混ぜれば、後者は titleset 2 に入ります。
  メニューは titleset 1 に置き、titleset をまたぐジャンプは dvdauthor の jumppad、別 titleset のタイトルから
  メニューへの復帰は VMGM のトップメニュー経由です（その titleset について dvdauthor が
  「creating a dummy menu」と出しますが想定どおりです）。
* **ハイライト**は自前のエンコーダ（`zlib`＋`struct`）で書いた 2bit インデックス PNG を spumux に渡しています。

## 動作確認

自動：`python -m unittest` で単体テストと、ツールが揃っていれば E2E テストが走ります。
E2E ではサンプル ISO を作って ffprobe / xorriso で中身を検査し、**libdvdnav（VLC が使う
DVD ナビゲーションライブラリ）でメニューのボタンを実際に押して**、チャプタージャンプと
メニュー復帰を確認します。

手動：

* **VLC** — `vlc dvd:///path/to/demo.iso`。メニュー、ボタン移動、チャプタージャンプ、
  メニュー復帰が動作します（Linux の VLC 3.0.20 でリモコン操作キーを送って確認済み）。
  GUI から `.iso` を開く方法も同様に動くはずですが、macOS ではまだ確認していません。
* **mpv** — `mpv dvd://0 --dvd-device=demo.iso` でタイトル 1（`dvd://1` でタイトル 2）を再生。
  mpv は **DVD メニューに非対応**（公式マニュアルに明記）なので、タイトルの確認用です。
  タイトル終了後はディスクのプログラムに従ってメニューに入り、操作できないままループするので `q` で終了してください。
* **macOS の「DVD プレーヤー」** — ISO をダブルクリックしてマウントし、
  「ファイル」→「DVD メディアを開く…」でマウントした `VIDEO_TS` フォルダを選びます
  （macOS 26 の DVD プレーヤー 6.0 で VIDEO_TS フォルダを開けることは Apple のガイドに記載）。
  oncemore の出力での動作は **まだ未確認** です。報告を歓迎します。
* **書き込み** — macOS は Finder または `hdiutil burn demo.iso`、Linux は
  `growisofs -dvd-compat -Z /dev/dvd=demo.iso`。oncemore 自体は書き込みを行いません。

## 既知の制限

* モーションメニューは動画 1 本のループのみ（アニメーションするボタンや遷移効果はなし）。
* 音声はステレオのみ（ダウンミックス）。字幕は SRT のみ、ディスク全体で 1 スタイル、
  下中央固定（字幕ごとの位置・色指定はなし）。
* 音声・字幕の n 番目のストリームの言語はディスク全体で 1 つ。メニューのアスペクト比は
  1 種類（`disc.aspect`）で、タイトルは個別に指定できます。
* フレームレート変換は単純な間引き／複製（テレシネ／逆テレシネなし）。インターレース素材は
  デインターレースしてプログレッシブで出力。
* `end_action` の連鎖以外の「全部再生して戻る」ロジックはなし。
* `xorriso` は UDF を書けないため、xorriso で作った ISO は ISO 9660 のみとなり、
  libdvdread 系プレーヤー（VLC、mpv）や多くの DVD プレーヤーで **開けません**。
  そのため hdiutil / genisoimage / mkisofs を優先し、xorriso にフォールバックした場合は警告します。
* ハイライトは 2bit サブピクチャなので縁が硬い。フォントはディスク全体で 1 種類。
  drawtext にはフォールバックが無いため、全文字がそのフォントに含まれている必要があります。
  oncemore はフォントの文字マップを検査し、豆腐（空の箱）を描く前に停止します。絵文字は非対応。
* `hdiutil` で作った ISO では、libdvdnav 系プレーヤー（VLC など）のディスク名メタデータが空になります。
  libdvdnav はディスク名をセクタ 32 から直接読みますが（実 DVD と genisoimage はここに UDF の記述子を置く）、
  hdiutil は別の位置に置くためです。UDF / ISO 9660 のボリューム名自体は正しく入っており（テストで確認）、
  再生には影響しません。
* コピーガードなし（設計方針として今後も入れません）。

## ライセンス

GPL-3.0-or-later（[LICENSE](LICENSE)）。dvdauthor が GPL のため揃えています。
「Encore」「Adobe」は各社の商標であり、oncemore は Adobe とは無関係です。
