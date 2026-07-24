# Cloud TTS エピソード 出荷前 QA チェックリスト

> ある回 (コワレフスカヤ) で user に読み誤り・速度・Manim 図・内容妥当性を **1 つずつ指摘させた**反省から整備した、Cloud TTS (Chirp3-HD) 専用の層別 QA。
> 目的: 「合成後に人が耳で拾う」前に、**多読み漢字/同音誤解語/難語/不自然な間/速度の平坦化/Manim 図の意味・衝突**を自動で洗い出す。

VOICEVOX は `audio_query` で kana を事前実測できる (`reading_guard.py`) が、Cloud には kana を返す口が無い。よって **予防 (合成前静的 lint) + 検出 (合成後 STT/Vision) の二段**で守る。

---

## 層別ツール (pipeline は engine=cloud で自動実行)

| 層 | タイミング | ツール | 捕えるもの |
|---|---|---|---|
| 予防 | script 後 / audio 前 | `scripts/cloud_reading_lint.py` | ① 多読み漢字が narration にあり narration_speech_cloud で読み未固定 ② 同音誤解語 (大数学者⇔代数学者) ③ 難語 (里程標) ④ 不自然な間の構文 (用言+とは / 長主語+は) |
| 検出 | audio 後 | `scripts/stt_qa.py` | 合成 wav を Gemini でカタカナ書き起こし → 助詞 は=ハ + **多読み漢字の文脈依存誤読** (`_READING_CHECKS`: 入れ→イレ, 愛→メ, 友→ユウ, 私→ワタクシ, 正→ショウ, 通→カヨ) を narration×STT で照合 |
| 検出 | audio 後 | `scripts/cloud_speed_qa.py` | 隣接文の速度段差 (>18%) + **速度プロファイル照合** (median/stdev/min を承認済み基準と比較。stdev<0.25=一本調子, median>7.7=速い, min>6.3=緩急なし) + 間・区切り異常 (run-on / over-pause / dash) |
| 検出 | visuals 後 | `scripts/manim_vision_qa.py` | Manim/route_map/timeline フレームを Claude Sonnet vision で「概念が伝わるか/無意味な動き/判別不能な形 (独楽が独楽に見えるか)/ラベル衝突」判定 (決定論 lint が捕まえない意味・美観) |

すべて **advisory** (WARN、既定 exit 0、`--strict` で exit 1)。build を止めず「まず見るべき箇所」を提示する。GOOGLE_API_KEY / Claude CLI 不在は graceful skip。

---

## 速度正規化の規律

`cloud_speed_qa.py --apply` は文単位速度を median へ atempo 正規化する。**ある回 では 2 回掛けて緩急 (stdev) を 0.60→0.26→0.18 と潰し「一本調子で速い」音声にした**。承認済み ある回 は単一適用で stdev 0.40 (遅い山場が残り自然)。

- **多重適用ガード**: `_prenorm_backup/` が既にあれば `--apply` は**良性スキップ (exit 0)**。かけ直すには `--restore` で原本に戻してから。緊急脱出は `--force`。pipeline の `--normalize-cloud-speed` と手動 `--apply` の重ね掛け事故を防ぐ。
- **速度が速いと感じたら**: まず正規化の多重掛けを疑う (プロファイル stdev をチェック)。基準速度そのものを下げるなら `episode_config.json` の `tts.rate` を下げる (rate 0.9≈median 7.4 / 0.85≈7.0)。**rate 変更時は音声を全再合成** (cache は config signature で無効化されるが、確実を期すなら audio/ の wav+cache+_prenorm_backup を消して cold 再合成)。
- 「本当に rate 通りか」の確認: `cloud_tts.py` は API に `speakingRate=config.tts.rate` を渡す。ログの `speedScale override` は **VOICEVOX 専用**で cloud には無関係。

---

## 出荷前チェックリスト (cloud ep)

1. **読み**: ビルド後 `stt_qa_report.txt` を開き、書き起こし全文を目視。cloud_reading_lint / stt_qa の WARN を潰す (多読みは narration_speech_cloud にひらがなで読み固定 or SSML phoneme、同音誤解語・難語は言い換え)。
2. **速度**: `speed_qa_report.txt` のプロファイル (median/stdev/min) を承認済み ep と照合。平坦化・過速を確認。**耳 spot-check 併用**。
3. **Manim/timeline**: manim_vision_qa の WARN + フレーム目視で「図が主張どおりに見えるか/無意味な動き/衝突」を確認。
4. **内容**: 難語・冗長・**不正確な関連付け** を目視。字幕は漢字維持・読みは narration_speech_cloud のみ変更 (字幕/音声の意味乖離に注意)。
5. 修正は原則 scene_definition.json のテキスト。**まとめて 1 回の再ビルド**で反映 (1 件ごとの再ビルドは高コスト)。

---

## 教訓 (最重要)

**Cloud 音声の読み検証は、テキスト層でなく実 wav を STT で** (過去の運用知見)。ある回 では、この決定打の phonetic-katakana STT (`stt_qa` の多読み照合) を proactively 回さず、テキスト層で「確認済み」と安心して user に全読み誤りを 1 つずつ指摘させた。**出荷前に必ず上記を回す**。
