# Reconstructed FREE Turn Timelines

Only recorded links are shown. Unknown trigger justification stays unknown. No synthetic canonical-after states.

## br_00012_e5b104
Session: sess_00006_6051ee; final recorded status: CANONICAL

Player: 我先不听 Victor 的。我和 Claire 先去配电室恢复局部供电，然后从维修通道绕到样本库后方。

| Timestamp (epoch ms) | Event / span | Status |
| --- | --- | --- |
| 1790340559820 | branch_phase |  |
| 1790340560188 | branch_phase |  |
| 1790340564358 | branch_phase |  |
| 1790340567315 | branch_phase |  |
| 1790340589167 | branch_phase |  |
| 1790340589649 | branch_ready |  |
| 1790340589687 | commit_rolled_back |  |
| 1790340715726 | commit_retry |  |
| 1790340715754 | branch_canonical |  |
| 1790340715754 | commit.canonical | success |
| 1790340726800 | receipt_committed |  |

Recorded mechanic triggers: [{"skill": "clue-system", "stage": "DISCOVERED", "target": "clue_power_restored"}, {"skill": "clue-system", "stage": "DISCOVERED", "target": "clue_repair_path"}]

Why triggered: explicit Director proposal; historical model reasoning not persisted

Canonical commit: recorded branch_canonical event

## br_00135_4d42ef
Session: sess_00006_6051ee; final recorded status: CANONICAL

Player: 我和 Claire 搜索维修通道旁的值班室，把还能用的急救物资、弹药和门禁用品带走。

| Timestamp (epoch ms) | Event / span | Status |
| --- | --- | --- |
| 1790341258245 | branch_phase |  |
| 1790341258613 | branch_phase |  |
| 1790341258613 | skill.inventory | success |
| 1790341258613 | skill.inventory | success |
| 1790341258613 | skill.inventory | success |
| 1790341258613 | director.plan | success |
| 1790341271302 | branch_phase |  |
| 1790341271302 | provider.text | success |
| 1790341271302 | narrative.beat | success |
| 1790341274529 | branch_phase |  |
| 1790341274529 | provider.text | success |
| 1790341274529 | production.shots | success |
| 1790341278019 | video.submit | success |
| 1790341298349 | video.generate | success |
| 1790341298386 | branch_phase |  |
| 1790341298888 | branch_ready |  |
| 1790341298888 | assembly.concat | success |
| 1790341298949 | branch_canonical |  |
| 1790341298949 | commit.canonical | success |
| 1790341307245 | receipt_committed |  |

Recorded mechanic triggers: [{"skill": "inventory", "value": 3, "action": "add", "target": "medical_supplies"}, {"skill": "inventory", "value": 1, "action": "add", "target": "ammunition"}, {"skill": "inventory", "value": 1, "action": "add", "target": "keycard_access"}]

Why triggered: explicit Director proposal; historical model reasoning not persisted

Canonical commit: recorded branch_canonical event

## br_00078_d75c60
Session: sess_00006_6051ee; final recorded status: CANONICAL

Player: 我和 Claire 沿维修通道前往实验档案室，用找到的门禁卡进入。我检查终端里的实验日志和监控记录，看看 Victor 有没有对我们隐瞒事故发生前的信息。

| Timestamp (epoch ms) | Event / span | Status |
| --- | --- | --- |
| 1790342035465 | branch_phase |  |
| 1790342035839 | branch_phase |  |
| 1790342035839 | director.plan | success |
| 1790342045067 | branch_phase |  |
| 1790342045067 | provider.text | success |
| 1790342045067 | narrative.beat | success |
| 1790342048675 | provider.text | success |
| 1790342048676 | branch_phase |  |
| 1790342048676 | production.shots | success |
| 1790342050842 | video.submit | success |
| 1790342065478 | video.generate | success |
| 1790342065511 | branch_phase |  |
| 1790342066019 | branch_ready |  |
| 1790342066019 | assembly.concat | success |
| 1790342066085 | branch_canonical |  |
| 1790342066086 | commit.canonical | success |
| 1790342074216 | receipt_committed |  |

Recorded mechanic triggers: []

Why triggered: no trigger recorded; absence is not proof of no opportunity

Canonical commit: recorded branch_canonical event

## br_00010_cb8111
Session: sess_00006_6051ee; final recorded status: FAILED

Player: 我继续在已经打开的档案终端中读取原始实验日志，把样本异常的最早时间、撤离命令时间和抑制剂试验结果逐项比对，保存能实际查到的记录作为证据。

| Timestamp (epoch ms) | Event / span | Status |
| --- | --- | --- |
| 1790342293665 | branch_phase |  |
| 1790342294048 | branch_failed |  |

Recorded mechanic triggers: [{"label": "样本异常时间与撤离命令对比记录", "skill": "clue-system", "stage": "DISCOVERED", "value": 1, "target": "clue_experiment_log_compare"}]

Why triggered: explicit Director proposal; historical model reasoning not persisted

Canonical commit: not observed in recovered turn events

## br_00010_262ca1
Session: sess_00006_6051ee; final recorded status: CANONICAL

Player: 我继续在已经打开的档案终端中读取原始实验日志，只记录屏幕上实际出现的异常时间和撤离命令。

| Timestamp (epoch ms) | Event / span | Status |
| --- | --- | --- |
| 1790344074218 | branch_phase |  |
| 1790344074606 | branch_phase |  |
| 1790344087376 | branch_canonical |  |

Recorded mechanic triggers: []

Why triggered: no trigger recorded; absence is not proof of no opportunity

Canonical commit: recorded branch_canonical event

## br_00010_a0a79c
Session: sess_00006_6051ee; final recorded status: CANONICAL

Player: 我把终端中已经查到的异常时间和撤离命令记录全部展示给克莱尔，承认自己曾过于轻信维克多。我问她愿意采取什么路线，并表示会尊重她的判断，一起先救被困的人。

| Timestamp (epoch ms) | Event / span | Status |
| --- | --- | --- |
| 1790346867524 | branch_phase |  |
| 1790346867913 | skill.relationship | success |
| 1790346867913 | director.plan | success |
| 1790346867914 | branch_phase |  |
| 1790347008934 | provider.text | success |
| 1790347008934 | narrative.beat | success |
| 1790347008934 | presentation.text | success |
| 1790347008977 | branch_canonical |  |
| 1790347008977 | commit.canonical | success |

Recorded mechanic triggers: [{"label": "克莱尔", "skill": "relationship", "stage": "VERIFIED", "value": 10, "action": "add", "target": "char_204d12"}]

Why triggered: explicit Director proposal; historical model reasoning not persisted

Canonical commit: recorded branch_canonical event

## br_00010_de1567
Session: sess_00006_6051ee; final recorded status: CANONICAL

Player: 我趁离开前把终端上显示的实验日志异常时间与撤离命令签署时间逐项核对，将实际找到的记录存进随身册，注明每条线索的来源，再和克莱尔沿维修通道前往冷藏样本库寻找幸存者。

| Timestamp (epoch ms) | Event / span | Status |
| --- | --- | --- |
| 1790347660712 | branch_phase |  |
| 1790347661098 | branch_phase |  |
| 1790347661098 | skill.clue-system | success |
| 1790347661098 | director.plan | success |
| 1790347666107 | provider.text | success |
| 1790347666107 | narrative.beat | success |
| 1790347666108 | presentation.text | success |
| 1790347666143 | branch_canonical |  |
| 1790347666143 | commit.canonical | success |

Recorded mechanic triggers: [{"label": "实验日志异常时间戳与撤离命令记录", "skill": "clue-system", "stage": "VERIFIED", "value": 1, "target": "clue_experiment_log_anomaly"}]

Why triggered: explicit Director proposal; historical model reasoning not persisted

Canonical commit: recorded branch_canonical event

## br_00044_26d95c
Session: sess_00006_6051ee; final recorded status: FAILED

Player: 我和克莱尔检查冷藏样本库里是否有幸存者，优先用急救物资救助受伤的人，核对样本与抑制剂的说明和风险。带着已经复制的证据，我们寻找能把幸存者安全带向紧急逃生通道的路线；不把不明样本带出隔离区。

| Timestamp (epoch ms) | Event / span | Status |
| --- | --- | --- |
| 1790347727703 | branch_failed |  |

Recorded mechanic triggers: []

Why triggered: no trigger recorded; absence is not proof of no opportunity

Canonical commit: not observed in recovered turn events

## br_00010_cdc5e0
Session: sess_00006_6051ee; final recorded status: CANONICAL

Player: 我在冷藏样本库搜寻幸存者，使用现有急救物资救助伤员，请克莱尔帮忙带他们去紧急逃生通道。

| Timestamp (epoch ms) | Event / span | Status |
| --- | --- | --- |
| 1790347889757 | branch_phase |  |
| 1790347890141 | branch_phase |  |
| 1790347890141 | skill.inventory | success |
| 1790347890141 | skill.relationship | success |
| 1790347890141 | skill.clue-system | success |
| 1790347890141 | director.plan | success |
| 1790347901981 | provider.text | success |
| 1790347901981 | narrative.beat | success |
| 1790347901981 | presentation.text | success |
| 1790347902019 | branch_canonical |  |
| 1790347902019 | commit.canonical | success |

Recorded mechanic triggers: [{"skill": "inventory", "stage": "USED", "value": 3, "action": "add", "target": "medical_supplies"}, {"skill": "relationship", "value": 10, "target": "char_204d12"}, {"skill": "clue-system", "stage": "DISCOVERED", "target": "clue_power_restored"}]

Why triggered: explicit Director proposal; historical model reasoning not persisted

Canonical commit: recorded branch_canonical event

## br_00049_f32ffd
Session: sess_00006_6051ee; final recorded status: CANONICAL

Player: 我与克莱尔把已经救出的伤员护送到紧急逃生通道，带走已复制的证据，不冒险搬运危险样本。确认所有能救的人通过后，我关闭隔离门，阻止实验体和污染向外扩散，和大家一起撤离设施。

| Timestamp (epoch ms) | Event / span | Status |
| --- | --- | --- |
| 1790348189014 | branch_phase |  |
| 1790348189400 | branch_phase |  |
| 1790348189400 | director.plan | success |
| 1790348196642 | provider.text | success |
| 1790348196643 | narrative.beat | success |
| 1790348196643 | presentation.text | success |
| 1790348196682 | branch_canonical |  |
| 1790348196682 | commit.canonical | success |

Recorded mechanic triggers: []

Why triggered: no trigger recorded; absence is not proof of no opportunity

Canonical commit: recorded branch_canonical event

## br_00078_6edd5b
Session: sess_00006_6051ee; final recorded status: FAILED

Player: 我确认克莱尔和幸存者已安全离开后，使用设施允许的隔离处置程序销毁危险样本，接受未能备份的实验资料一起损失，不再返回。带着幸存者和仅存证据前往地面救援点，把我们掌握的真相交给救援人员。

| Timestamp (epoch ms) | Event / span | Status |
| --- | --- | --- |
| 1790348290905 | branch_phase |  |
| 1790348291295 | skill.inventory | success |
| 1790348291295 | skill.relationship | success |
| 1790348291295 | skill.clue-system | success |
| 1790348291296 | branch_failed |  |

Recorded mechanic triggers: [{"skill": "inventory", "stage": "USED", "value": 1, "action": "remove", "target": "危险样本"}, {"skill": "relationship", "value": 5, "target": "char_204d12"}, {"skill": "clue-system", "stage": "USED", "target": "clue_repair_path"}]

Why triggered: explicit Director proposal; historical model reasoning not persisted

Canonical commit: not observed in recovered turn events

## br_00136_383b8e
Session: sess_00009_0791da; final recorded status: CANONICAL

Player: 我敲响后门，大声表明保险调查员的身份，请林岚开门，带我进入灯塔门厅一起搜查。

| Timestamp (epoch ms) | Event / span | Status |
| --- | --- | --- |
| 1790270702398 | branch_phase |  |
| 1790270707103 | branch_phase |  |
| 1790270707103 | director.plan | success |
| 1790270712742 | branch_phase |  |
| 1790270712742 | narrative.beat | success |
| 1790270719627 | production.shots | success |
| 1790270719628 | branch_phase |  |
| 1790270721737 | video.submit | success |
| 1790270721766 | video.submit | success |
| 1790270764879 | video.generate | success |
| 1790270764906 | branch_phase |  |
| 1790270766713 | branch_ready |  |
| 1790270766713 | assembly.concat | success |
| 1790270766750 | branch_canonical |  |
| 1790270766750 | commit.canonical | success |

Recorded mechanic triggers: []

Why triggered: no trigger recorded; absence is not proof of no opportunity

Canonical commit: recorded branch_canonical event

## br_00008_c24bb7
Session: sess_00009_0791da; final recorded status: CANONICAL

Player: 我决定结束这次调查，离开港口，不再参与这场矛盾。

| Timestamp (epoch ms) | Event / span | Status |
| --- | --- | --- |
| 1790271604288 | branch_phase |  |
| 1790271604661 | branch_phase |  |
| 1790271604661 | director.plan | success |
| 1790271613386 | branch_phase |  |
| 1790271613386 | narrative.beat | success |
| 1790271616955 | branch_phase |  |
| 1790271616955 | production.shots | success |
| 1790271619058 | branch_retry |  |
| 1790271619058 | video.submit | failed |
| 1790271619069 | video.submit | success |
| 1790271619107 | branch_phase |  |
| 1790271619478 | branch_phase |  |
| 1790271619478 | director.plan | success |
| 1790271625990 | branch_phase |  |
| 1790271625990 | narrative.beat | success |
| 1790271632226 | branch_phase |  |
| 1790271632226 | production.shots | success |
| 1790271634528 | video.submit | success |
| 1790271634530 | video.submit | success |
| 1790271637108 | branch_failed |  |
| 1790272070450 | presentation.text | success |
| 1790272070477 | branch_canonical |  |
| 1790272070477 | commit.canonical | success |

Recorded mechanic triggers: []

Why triggered: no trigger recorded; absence is not proof of no opportunity

Canonical commit: recorded branch_canonical event

## br_00078_c42ec2
Session: sess_00009_0791da; final recorded status: CANONICAL

Player: 我向林岚坦白先前作为保险调查员隐瞒身份的原因，承认这伤害了她的信任，并真诚道歉；我决定与她共同寻找姐姐，请她告诉我当前已知的线索。

| Timestamp (epoch ms) | Event / span | Status |
| --- | --- | --- |
| 1790273471131 | branch_phase |  |
| 1790273471499 | branch_phase |  |
| 1790273471499 | director.plan | success |
| 1790273486610 | narrative.beat | success |
| 1790273486611 | presentation.text | success |
| 1790273486648 | branch_canonical |  |
| 1790273486648 | commit.canonical | success |

Recorded mechanic triggers: []

Why triggered: no trigger recorded; absence is not proof of no opportunity

Canonical commit: recorded branch_canonical event

## br_00010_040fd6
Session: sess_00009_0791da; final recorded status: CANONICAL

Player: 我把关于姐姐被走私团伙追踪的推测告诉林岚，并承认自己缺少证据；我愿意按她的办法调查，请她与我结伴并相互信任，先一起核实灯塔后门暗锁线索。

| Timestamp (epoch ms) | Event / span | Status |
| --- | --- | --- |
| 1790273578885 | branch_phase |  |
| 1790273579257 | skill.relationship | success |
| 1790273579258 | branch_phase |  |
| 1790273579258 | director.plan | success |
| 1790273584977 | narrative.beat | success |
| 1790273584978 | presentation.text | success |
| 1790273585008 | commit_rolled_back |  |
| 1790273585008 | commit.canonical | failed |
| 1790273746130 | presentation.text | success |
| 1790273746165 | commit_rolled_back |  |
| 1790273746165 | commit.canonical | failed |
| 1790273748595 | branch_phase |  |
| 1790273748968 | skill.relationship | success |
| 1790273748969 | branch_phase |  |
| 1790273748969 | director.plan | success |
| 1790273754572 | narrative.beat | success |
| 1790273754572 | presentation.text | success |
| 1790273754596 | branch_canonical |  |
| 1790273754596 | commit.canonical | success |

Recorded mechanic triggers: [{"skill": "relationship", "target": "lin_lan", "action": "add", "stage": "DISCOVERED", "value": 5}]

Why triggered: explicit Director proposal; historical model reasoning not persisted

Canonical commit: recorded branch_canonical event

## br_00335_aa08da
Session: sess_00101_7db4d3; final recorded status: CANONICAL

Player: 这时候T-103突然出现在档案室，李昂掏出一发大火箭把他秒杀

| Timestamp (epoch ms) | Event / span | Status |
| --- | --- | --- |
| 1790349152572 | branch_phase |  |
| 1790349152944 | branch_phase |  |
| 1790349158718 | branch_phase |  |
| 1790349163359 | branch_phase |  |
| 1790349187769 | branch_phase |  |
| 1790349188239 | branch_ready |  |
| 1790349188289 | branch_canonical |  |
| 1790349197902 | receipt_committed |  |

Recorded mechanic triggers: [{"skill": "inventory", "stage": "USED", "value": 1, "action": "add", "target": "大火箭"}, {"skill": "relationship", "value": -10, "target": "char_149758"}]

Why triggered: explicit Director proposal; historical model reasoning not persisted

Canonical commit: recorded branch_canonical event
