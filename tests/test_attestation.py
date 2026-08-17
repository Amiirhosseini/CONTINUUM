"""Round-trip tests for the optional event-chain attestation primitives."""

from __future__ import annotations

from continuum.security.attestation import (
    ATTESTATION_ALGORITHM,
    Attestation,
    generate_keypair,
    sign_chain,
    verify_attestation,
)


def test_sign_and_verify_round_trip() -> None:
    priv_pem, pub_pem = generate_keypair()
    attest = sign_chain(
        priv_pem,
        run_id="run_abc",
        trusted_through_seq=42,
        chain_hash="abc123",
        signer="ci-bot",
    )
    assert isinstance(attest, Attestation)
    assert attest.algorithm == ATTESTATION_ALGORITHM
    assert attest.public_key == pub_pem
    assert verify_attestation(attest) is True
    assert verify_attestation(attest, expected_chain_hash="abc123") is True


def test_verify_rejects_wrong_chain_hash() -> None:
    priv_pem, _pub_pem = generate_keypair()
    attest = sign_chain(priv_pem, "run_abc", 42, "abc123")
    assert verify_attestation(attest, expected_chain_hash="tampered") is False


def test_verify_rejects_tampered_payload() -> None:
    priv_pem, _pub_pem = generate_keypair()
    attest = sign_chain(priv_pem, "run_abc", 42, "abc123")
    tampered = Attestation(
        **{**attest.to_dict(), "trusted_through_seq": 43}
    )
    assert verify_attestation(tampered) is False


def test_verify_rejects_substituted_public_key() -> None:
    priv_pem, _pub_pem = generate_keypair()
    _other_priv, other_pub = generate_keypair()
    attest = sign_chain(priv_pem, "run_abc", 42, "abc123")
    # An attacker swaps in a different public key but leaves the signature.
    swapped = Attestation(**{**attest.to_dict(), "public_key": other_pub})
    assert verify_attestation(swapped) is False
