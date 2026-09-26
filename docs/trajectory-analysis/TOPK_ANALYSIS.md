# Top-K Analysis

Real Jev ranking calls recovered: 11. OTHER > 0.5: 4. Ranking input contains only location ID, inventory, clues and empty raw_player_input; missing current beat, readable location, relationships, pressure, player preference. OTHER is discarded during sorting. This is stronger evidence of context starvation than of semantic duplication.

| Session | Candidates | OTHER |
| --- | --- | --- |
| sess_00006_6051ee | 恢复配电与分流电力; 从维修通道潜入样本库; 优先保护幸存者并撤离; 向 Victor 寻求短暂撤离协议; 搜寻并保留关键犯罪证据 | 0.09 |
| sess_00006_6051ee | 重新分配剩余电力; 撤离与撤退; 潜入样本库取回关键证据; 协助克莱尔寻找幸存者; 与Victor Hale博士博弈 | 0.45 |
| sess_00006_6051ee | 维修通道防线; 档案室伏击; 真相交涉; 冷藏牺牲 | 0.45 |
| sess_00006_6051ee | 搜查控制中心获取钥匙; 护送幸存者至避难所; 破坏样本冷藏以阻止扩散; 与 Victor 进行最后谈判; 分心与牺牲 | 0.87 |
| sess_00006_f91c09 | 查阅实验档案寻找证据; 进入配电室恢复供电; 护送幸存者前往安全出口; 与克莱尔协调分工; 冒险一搏：潜入冷藏样本库 | 0.95 |
| sess_00006_6051ee | 深入检查配电箱; 优先转移幸存者; 威胁 Victor 的实验记录; 掩盖病毒样本踪迹 | 0.41 |
| sess_00006_97bc74 | 优先撤离关键幸存者; 收集并转移关键证据; 检查配电系统; 与 Victor 博士博弈; 设局引诱 T-103 | 0.93 |
| acceptance_lead_final | 离开码头; 询问维修员姐姐; 查看灯塔门厅; 检查后门锁孔; 深入地下维修间 | 0.73 |
| sess_00009_0791da | 检查码头设施; 询问维修员细节; 查看灯塔门厅; 询问守塔人的近况; 暂时退回避风险 | 0.17 |
| sess_00009_0791da | 查看码头边缘的痕迹; 询问林岚关于灯塔后门的细节; 检查灯塔大门的锁状态; 深入查问林岚的姐姐近况; 返回警局报备情况 | 0.33 |
| sess_00009_0791da | 查看码头边缘的痕迹; 返回码头小屋暂避风雨; 询问林兰关于后门的细节; 前往灯塔门厅观察内部情况 | 0.43 |


Candidates generally contain investigation/social/rescue/withdrawal alternatives. No validated corpus establishes frequent synonym-only triples. Do not add a separate diversity model call or force absurd choices. Evaluate lexical similarity as a screening proxy only; preserve Jev rank and report OTHER uncertainty. Exact normalized duplicate filtering and richer ranking context are justified; semantic MMR requires a labeled benchmark before deployment.

## Post-implementation evaluation

Three real Director/Jev counterfactuals, equal Top-3 blinded review: new 2 / old 1. Diversity ratings 4→3, 3→4, 3→4; small sample. Initial five-versus-three evaluation excluded. Repeated completed goals remain possible. See pairwise_choices/ and evaluation_metrics.json.
