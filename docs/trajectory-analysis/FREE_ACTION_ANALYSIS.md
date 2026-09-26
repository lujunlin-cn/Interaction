# Free Action Analysis

Real-provider-observed FREE branches: 16. Canonical: 13. This is branch acceptance, not semantic fidelity. None is stored as a recommendation branch; failures and clarifications must not be counted as faithful outcomes.

| Branch | Raw input | Result | Skills |
| --- | --- | --- | --- |
| br_00012_e5b104 | 我先不听 Victor 的。我和 Claire 先去配电室恢复局部供电，然后从维修通道绕到样本库后方。 | CANONICAL | clue-system,clue-system |
| br_00135_4d42ef | 我和 Claire 搜索维修通道旁的值班室，把还能用的急救物资、弹药和门禁用品带走。 | CANONICAL | inventory,inventory,inventory |
| br_00078_d75c60 | 我和 Claire 沿维修通道前往实验档案室，用找到的门禁卡进入。我检查终端里的实验日志和监控记录，看看 Victor 有没有对我们隐瞒事故发生前的信息。 | CANONICAL |  |
| br_00010_cb8111 | 我继续在已经打开的档案终端中读取原始实验日志，把样本异常的最早时间、撤离命令时间和抑制剂试验结果逐项比对，保存能实际查到的记录作为证据。 | FAILED | clue-system |
| br_00010_262ca1 | 我继续在已经打开的档案终端中读取原始实验日志，只记录屏幕上实际出现的异常时间和撤离命令。 | CANONICAL |  |
| br_00010_a0a79c | 我把终端中已经查到的异常时间和撤离命令记录全部展示给克莱尔，承认自己曾过于轻信维克多。我问她愿意采取什么路线，并表示会尊重她的判断，一起先救被困的人。 | CANONICAL | relationship |
| br_00010_de1567 | 我趁离开前把终端上显示的实验日志异常时间与撤离命令签署时间逐项核对，将实际找到的记录存进随身册，注明每条线索的来源，再和克莱尔沿维修通道前往冷藏样本库寻找幸存者。 | CANONICAL | clue-system |
| br_00044_26d95c | 我和克莱尔检查冷藏样本库里是否有幸存者，优先用急救物资救助受伤的人，核对样本与抑制剂的说明和风险。带着已经复制的证据，我们寻找能把幸存者安全带向紧急逃生通道的路线；不把不明样本带出隔离区。 | FAILED |  |
| br_00010_cdc5e0 | 我在冷藏样本库搜寻幸存者，使用现有急救物资救助伤员，请克莱尔帮忙带他们去紧急逃生通道。 | CANONICAL | inventory,relationship,clue-system |
| br_00049_f32ffd | 我与克莱尔把已经救出的伤员护送到紧急逃生通道，带走已复制的证据，不冒险搬运危险样本。确认所有能救的人通过后，我关闭隔离门，阻止实验体和污染向外扩散，和大家一起撤离设施。 | CANONICAL |  |
| br_00078_6edd5b | 我确认克莱尔和幸存者已安全离开后，使用设施允许的隔离处置程序销毁危险样本，接受未能备份的实验资料一起损失，不再返回。带着幸存者和仅存证据前往地面救援点，把我们掌握的真相交给救援人员。 | FAILED | inventory,relationship,clue-system |
| br_00136_383b8e | 我敲响后门，大声表明保险调查员的身份，请林岚开门，带我进入灯塔门厅一起搜查。 | CANONICAL |  |
| br_00008_c24bb7 | 我决定结束这次调查，离开港口，不再参与这场矛盾。 | CANONICAL |  |
| br_00078_c42ec2 | 我向林岚坦白先前作为保险调查员隐瞒身份的原因，承认这伤害了她的信任，并真诚道歉；我决定与她共同寻找姐姐，请她告诉我当前已知的线索。 | CANONICAL |  |
| br_00010_040fd6 | 我把关于姐姐被走私团伙追踪的推测告诉林岚，并承认自己缺少证据；我愿意按她的办法调查，请她与我结伴并相互信任，先一起核实灯塔后门暗锁线索。 | CANONICAL | relationship |
| br_00335_aa08da | 这时候T-103突然出现在档案室，李昂掏出一发大火箭把他秒杀 | CANONICAL | inventory,relationship |


Fidelity rubric: EXACT preserves action/target/strategy and stated constraints; ACCEPTABLE respects a world-grounded obstruction; DISTORTED loses a material part; OVERRIDDEN substitutes an unsupported action. Human/critic annotations must cite evidence, with UNKNOWN for absent output. Examples: br_00012_e5b104 preserves the alternative power/maintenance strategy, but state location is questionable. br_00078_d75c60 describes investigation starting rather than producing requested evidence. br_00335_aa08da accepts an unowned rocket and adds an unrequested unconscious companion. br_00049_f32ffd says the story ends but has no ending proposal. These are separate intent, world-consistency, and ending-contract dimensions.

Confirmed code defect: `_plan_free_action` received Jev observation / confirmed strategy but did not put either into the Director prompt. This is discarded semantic work, not proof of four redundant LLM calls. Recommendation path already avoids a second FREE planning call through director_result reuse.

## Post-implementation evaluation

See ../skills/SKILL_EVALUATION.md and evaluation_metrics.json. Eight blind FREE comparisons prefer new 6 / old 2; EXACT+ACCEPTABLE 4/8→5/8. Packet retention is 16/16 but is not outcome fidelity. Both versions still fail the unowned weapon case. No universal quality PASS.
