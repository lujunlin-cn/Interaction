# Biohazard E2E 阶段耗时

2026-09-25T15:00:18.859466+00:00

真实时间戳统计；流水线阶段含调度等待，H3含排队和轮询；人工/QA/调试时间不计生成。缺失历史数据不估算。

| 阶段 | 次数 | 总s | 平均s | 中位s | 最长s |
|---|---:|---:|---:|---:|---:|
| 4K Image HTTP | 13 | 543.687 | 41.822 | 41.172 | 48.888 |
| H3 queue/generation/poll | 20 | 385.505 | 19.275 | 18.981 | 29.172 |
| Step5 QA (timed calls only) | 9 | 381.907 | 42.434 | 38.7 | 87.31 |
| director / nemotron_local / nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4 | 38 | 350.592 | 9.226 | 6.774 | 59.436 |
| narrative / step_37 / step-3.7-flash | 22 | 275.831 | 12.538 | 12.16 | 20.621 |
| production / nemotron_local / nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4 | 17 | 57.803 | 3.4 | 3.283 | 4.895 |

## Scene各阶段墙钟

| Branch | 状态 | 创建至READY | Planning | Narrative | Production | Generating | Assembling | READY后审核/调试等待 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| opening_00011_8a86b8 | opening/CANONICAL | 60.369 | 13.805 | 18.799 | 3.652 | 23.637 | 0.464 | 0.032 |
| br_00057_333e2c | recommendation/INVALIDATED | 83.617 | 4.554 | 28.502 | 28.195 | 21.857 | 0.458 | 未测量 |
| br_00059_35f225 | recommendation/INVALIDATED | 95.159 | 10.712 | 34.12 | 19.954 | 29.844 | 0.468 | 未测量 |
| br_00061_8b5055 | recommendation/INVALIDATED | 93.707 | 17.598 | 41.143 | 9.079 | 25.353 | 0.461 | 未测量 |
| br_00012_e5b104 | free/CANONICAL | 29.86 | 0.368 | 4.17 | 2.957 | 21.852 | 0.482 | 126.105 |
| br_00014_5436a7 | recommendation/INVALIDATED | 92.357 | 5.815 | 19.423 | 25.557 | 40.972 | 0.465 | 未测量 |
| br_00016_971354 | recommendation/CANONICAL | 88.428 | 11.45 | 26.769 | 15.878 | 33.704 | 0.489 | 29.102 |
| br_00018_cd8309 | recommendation/INVALIDATED | 80.836 | 17.887 | 30.39 | 9.456 | 22.468 | 0.482 | 未测量 |
| br_00014_c29e0e | recommendation/INVALIDATED | 78.606 | 5.365 | 26.018 | 26.075 | 20.576 | 0.462 | 未测量 |
| br_00016_0227c3 | recommendation/INVALIDATED | 87.212 | 9.417 | 33.147 | 17.881 | 26.176 | 0.464 | 未测量 |
| br_00018_480454 | recommendation/INVALIDATED | 88.925 | 16.667 | 37.925 | 9.159 | 24.529 | 0.501 | 未测量 |
| br_00135_4d42ef | free/CANONICAL | 40.677 | 0.368 | 12.689 | 3.227 | 23.857 | 0.502 | 0.061 |
| br_00187_55f559 | recommendation/INVALIDATED | 110.979 | 9.014 | 36.249 | 33.179 | 31.888 | 0.472 | 未测量 |
| br_00189_e7f016 | recommendation/INVALIDATED | 109.695 | 18.496 | 39.338 | 23.687 | 27.466 | 0.504 | 未测量 |
| br_00191_ddf574 | recommendation/INVALIDATED | 110.348 | 31.909 | 42.512 | 11.329 | 23.899 | 0.469 | 未测量 |
| br_00078_d75c60 | free/CANONICAL | 30.589 | 0.374 | 9.228 | 3.609 | 16.835 | 0.508 | 0.067 |
| br_00155_bbf735 | recommendation/INVALIDATED | 未测量 | 41.902 | 未测量 | 未测量 | 未测量 | 未测量 | 未测量 |
| br_00157_2ebe77 | recommendation/INVALIDATED | 未测量 | 46.459 | 未测量 | 未测量 | 未测量 | 未测量 | 未测量 |
| br_00159_53d1e8 | recommendation/INVALIDATED | 未测量 | 52.819 | 未测量 | 未测量 | 未测量 | 未测量 | 未测量 |
| br_00010_cb8111 | free/FAILED | 未测量 | 未测量 | 未测量 | 未测量 | 未测量 | 未测量 | 未测量 |
| br_00010_262ca1 | free/CANONICAL | 未测量 | 0.388 | 未测量 | 未测量 | 未测量 | 未测量 | 未测量 |
| br_00010_a0a79c | free/CANONICAL | 未测量 | 0.39 | 未测量 | 未测量 | 未测量 | 未测量 | 未测量 |
| br_00010_de1567 | free/CANONICAL | 未测量 | 0.386 | 未测量 | 未测量 | 未测量 | 未测量 | 未测量 |
| br_00044_26d95c | free/FAILED | 未测量 | 未测量 | 未测量 | 未测量 | 未测量 | 未测量 | 未测量 |
| br_00010_cdc5e0 | free/CANONICAL | 未测量 | 0.384 | 未测量 | 未测量 | 未测量 | 未测量 | 未测量 |
| br_00049_f32ffd | free/CANONICAL | 未测量 | 0.386 | 未测量 | 未测量 | 未测量 | 未测量 | 未测量 |
| br_00078_6edd5b | free/FAILED | 未测量 | 未测量 | 未测量 | 未测量 | 未测量 | 未测量 | 未测量 |
| opening_00011_3d2895 | opening/CANONICAL | 432.516 | 11.897 | 12.803 | 390.437 | 16.887 | 0.48 | 0.022 |
| br_00048_7acf37 | recommendation/READY | 100.934 | 7.054 | 25.098 | 31.501 | 36.736 | 0.488 | 未测量 |
| br_00050_30002e | recommendation/READY | 96.695 | 12.111 | 33.598 | 20.884 | 29.528 | 0.505 | 未测量 |
| br_00052_e1e4c2 | recommendation/READY | 103.39 | 16.93 | 41.794 | 11.562 | 32.539 | 0.486 | 未测量 |

FREE初次Director可能早于Branch创建；创建至READY不是完整点击到播放。Provider耗时来自独立trace，不能与阶段驻留重复相加。

## 推荐整批READY

| Epoch | 分支数 | 曾READY | 整批墙钟s |
|---|---:|---:|---:|

逐请求明细与来源ID：docs/acceptance/biohazard_full_e2e/phase_timings.json。
