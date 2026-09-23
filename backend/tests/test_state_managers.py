"""StateManager / DramaStateManager 单元测试（对应原型 runChecks 的核心不变量）。"""
import pytest

from app.domain.drama_manager import DramaStateManager
from app.domain.schemas import (
    DramaPatchProposal, DramaState, ForeshadowEntry, PatchOperation, StatePatchProposal,
    WorldState,
)
from app.domain.state_manager import ProposalRejected, StateManager, apply_operations


def make_world() -> WorldState:
    return WorldState(version=1, location="foyer", inventory=[], relationships={"alice": 42})


def make_proposal(ops, base=1, key="k1") -> StatePatchProposal:
    return StatePatchProposal(
        proposal_id="p1", base_version=base, operations=ops, idempotency_key=key)


class TestStateManager:
    def setup_method(self):
        self.sm = StateManager()

    def test_whitelist_set(self):
        w = self.sm.validate(make_world(), make_proposal(
            [PatchOperation(op="set", path="location", value="backyard")]), [])
        assert w.location == "backyard"
        assert w.version == 2

    def test_forbidden_path_rejected(self):
        with pytest.raises(ProposalRejected):
            self.sm.validate(make_world(), make_proposal(
                [PatchOperation(op="set", path="truth.fact_recording", value="x")]), [])

    def test_proto_pollution_rejected(self):
        with pytest.raises(ProposalRejected):
            apply_operations(make_world(),
                             [PatchOperation(op="set", path="objects.__proto__.x", value=1)])

    def test_stale_base_version_rejected(self):
        with pytest.raises(ProposalRejected, match="stale"):
            self.sm.validate(make_world(), make_proposal(
                [PatchOperation(op="set", path="location", value="x")], base=99), [])

    def test_idempotency(self):
        w = make_world()
        p = make_proposal([PatchOperation(op="set", path="location", value="room")], key="dup")
        self.sm.validate(w, p, [])
        with pytest.raises(ProposalRejected) as ei:
            self.sm.validate(w, p, ["dup"])
        assert ei.value.duplicate

    def test_relationship_clamped(self):
        w = self.sm.validate(make_world(), make_proposal(
            [PatchOperation(op="increment", path="relationships.alice", value=999)]), [])
        assert w.relationships["alice"] == 100

    def test_inventory_capacity(self):
        w = make_world()
        w.inventory = [f"item{i}" for i in range(8)]
        with pytest.raises(ProposalRejected, match="capacity"):
            self.sm.validate(w, make_proposal([PatchOperation(op="addItem", value="ninth")] ), [])

    def test_precondition_checked(self):
        p = make_proposal([PatchOperation(op="set", path="location", value="street")])
        p.preconditions = [{"path": "location", "equals": "foyer"}]
        self.sm.validate(make_world(), p, [])  # 满足
        p2 = make_proposal([PatchOperation(op="set", path="location", value="street")], key="k2")
        p2.preconditions = [{"path": "location", "equals": "backyard"}]
        with pytest.raises(ProposalRejected, match="precondition"):
            self.sm.validate(make_world(), p2, [])

    def test_original_not_mutated_on_failure(self):
        w = make_world()
        with pytest.raises(ProposalRejected):
            self.sm.validate(w, make_proposal([
                PatchOperation(op="set", path="location", value="room"),
                PatchOperation(op="set", path="forbidden", value=1),
            ]), [])
        assert w.location == "foyer" and w.version == 1


class TestDramaManager:
    def setup_method(self):
        self.dm = DramaStateManager()

    def _proposal(self, ops, base=1, key="d1") -> DramaPatchProposal:
        return DramaPatchProposal(proposal_id="dp1", base_revision=base,
                                  operations=ops, idempotency_key=key)

    def test_foreshadow_legal_transition(self):
        d = DramaState(foreshadows=[ForeshadowEntry(id="key_scratches")])
        d2 = self.dm.validate_and_apply(d, self._proposal(
            [{"op": "advance_foreshadow", "entry_id": "key_scratches", "to": "PLANTED"}]), [])
        assert d2.foreshadows[0].status.value == "PLANTED"
        assert d2.revision == 2

    def test_foreshadow_illegal_jump_rejected(self):
        d = DramaState(foreshadows=[ForeshadowEntry(id="f1")])
        with pytest.raises(ProposalRejected, match="illegal"):
            self.dm.validate_and_apply(d, self._proposal(
                [{"op": "advance_foreshadow", "entry_id": "f1", "to": "PAID_OFF"}]), [])

    def test_unknown_op_rejected(self):
        with pytest.raises(ProposalRejected, match="unknown"):
            self.dm.validate_and_apply(DramaState(), self._proposal(
                [{"op": "rewrite_truth"}]), [])

    def test_stale_revision_rejected(self):
        with pytest.raises(ProposalRejected, match="stale"):
            self.dm.validate_and_apply(DramaState(revision=3), self._proposal(
                [{"op": "set_phase", "phase": "CRISIS"}], base=1), [])
