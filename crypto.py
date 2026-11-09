"""Signed project declarations; local node policy is independently enforced."""
import hashlib
import json
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature
from .models import Project, SignedProject


def canonical(data) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def digest(data) -> str:
    return hashlib.sha256(canonical(data)).hexdigest()


def create_keypair(private_file: str, public_file: str) -> None:
    priv = Ed25519PrivateKey.generate()
    Path(private_file).write_bytes(priv.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    Path(private_file).chmod(0o600)
    Path(public_file).write_bytes(priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex().encode())


def sign_project(project: Project, private_file: str) -> SignedProject:
    priv = serialization.load_pem_private_key(Path(private_file).read_bytes(), password=None)
    if not isinstance(priv, Ed25519PrivateKey):
        raise ValueError('expected Ed25519 private key')
    pub = priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    sig = priv.sign(canonical(project.model_dump(mode='json'))).hex()
    return SignedProject(project=project, signer_pubkey=pub, signature=sig)


def verify_project(signed: SignedProject, trusted_signers: list[str]) -> bool:
    if signed.signer_pubkey not in trusted_signers:
        return False
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(signed.signer_pubkey)).verify(
            bytes.fromhex(signed.signature), canonical(signed.project.model_dump(mode='json'))
        )
        return True
    except (InvalidSignature, ValueError):
        return False
