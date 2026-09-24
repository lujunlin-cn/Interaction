# Real H3 Max Multi-Shot Acceptance

日期：2026-09-24  
判定：**PASS（真实 Provider 证据）**

本次使用 `FalH3MaxProvider` 和模型 `minimax/h3-max/reference-to-video`，没有走
`mock_video`。参考图使用公开可拉取的图片 URL。每个 Shot 都独立调用 queue submit，
再下载为本地 clip，最后用 FFmpeg concat demuxer 生成 SceneArtifact。

| Shot | Provider job/request | 状态 | clip | ffprobe 时长 |
| --- | --- | --- | --- | ---: |
| shot_1 | `01a0d2f5-3717-72d1-8667-cbd9e2440d9a` | READY | `data/media/clips/01a0d2f5-3717-72d1-8667-cbd9e2440d9a/clip_1.mp4` | 5.184s |
| shot_2 | `01a0d2f5-6c53-73e3-8fd1-15ae7aa4d3b8` | READY | `data/media/clips/01a0d2f5-6c53-73e3-8fd1-15ae7aa4d3b8/clip_1.mp4` | 5.184s |

两次 submit 的 prompt、参考图、submitted/completed 时间、Provider 原始回执和输出
文件均保存在 [`real_h3_multishot_evidence.json`](real_h3_multishot_evidence.json)。
最终装配产物为（仓库留存副本）：

```text
`docs/acceptance/evidence/real_acceptance_h3_multishot.mp4`

运行目录原件：`backend/data/media/scenes/real_acceptance_h3_multishot.mp4`。
```

FFmpeg 输入列表为 `data/media/scenes/real_acceptance_h3_multishot.txt`，按
`shot_1 → shot_2` 排序；`ffprobe(final)=10.400s`，clip 时长和为 `10.368s`，
差异来自 concat 重编码的时间基取整。运行时的 `_generate_video()` 也已按同一契约
记录 `shot_id/provider_job_id/prompt/references/submitted_at/completed_at/output_clips/
duration/status`，`SceneArtifact.provenance` 记录 `concat_inputs/final_output/
clip_durations/final_duration/shot_provenance`。

首次无 key 的请求被 Provider 拒绝（`Illegal header value b'Key '`），该失败原样保留在
脚本终端记录；随后使用后端 `.env` 中已配置的 key 重试并完成两 Shot。Mock fallback
没有计入本次 PASS。
