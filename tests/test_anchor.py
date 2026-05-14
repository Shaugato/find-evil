"""Merkle anchor math — root, inclusion proof, domain separation, verifiability."""

from __future__ import annotations

import hashlib

import blake3
import pytest

from findevil.ledger.anchor import (
    LEAF_DOM,
    NODE_DOM,
    merkle_copath,
    merkle_inclusion_proof,
    merkle_root,
)


def _b(x: str) -> bytes:
    return hashlib.sha256(x.encode()).digest()


def _verify_inclusion(leaf: bytes, proof: dict) -> bool:
    """Recompute the root from leaf + co-path and compare to `proof['root']`."""
    h = blake3.blake3(LEAF_DOM + leaf).digest()
    idx = proof["leaf_index"]
    for sib in proof["path"]:
        if idx % 2 == 0:
            h = blake3.blake3(NODE_DOM + h + sib).digest()
        else:
            h = blake3.blake3(NODE_DOM + sib + h).digest()
        idx //= 2
    return h == proof["root"]


def test_single_leaf_root_is_leaf_hash():
    leaves = [_b("a")]
    root = merkle_root(leaves)
    assert isinstance(root, bytes) and len(root) == 32


def test_inclusion_proof_verifies():
    leaves = [_b(str(i)) for i in range(8)]
    root = merkle_root(leaves)
    for idx in range(len(leaves)):
        proof = merkle_inclusion_proof(leaves, idx)
        assert proof["leaf_index"] == idx
        assert proof["tree_size"] == len(leaves)
        # balanced 8-leaf tree => path length == log2(8) == 3
        assert len(proof["path"]) == 3
        assert proof["root"] == root
        assert _verify_inclusion(leaves[idx], proof)


def test_copath_matches_proof_path():
    leaves = [_b(str(i)) for i in range(6)]  # odd-tier duplication path
    for idx in range(len(leaves)):
        assert merkle_copath(leaves, idx) == merkle_inclusion_proof(leaves, idx)["path"]


def test_empty_tree_raises():
    with pytest.raises(ValueError):
        merkle_root([])


def test_out_of_range_raises():
    leaves = [_b(str(i)) for i in range(4)]
    with pytest.raises(IndexError):
        merkle_inclusion_proof(leaves, 4)
    with pytest.raises(IndexError):
        merkle_copath(leaves, -1)
