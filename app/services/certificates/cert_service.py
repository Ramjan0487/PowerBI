"""
Digital Certificate Service — issue, verify, revoke PKI certificates for contracts
"""
import os
import hashlib
import secrets
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend


def load_ca():
    """Load CA key and certificate from disk."""
    ca_cert_path = os.getenv("MTLS_CA_CERT", "certs/ca/ca.crt")
    ca_key_path  = os.getenv("MTLS_CA_KEY",  "certs/ca/ca.key")
    with open(ca_cert_path, "rb") as f:
        ca_cert = x509.load_pem_x509_certificate(f.read(), default_backend())
    with open(ca_key_path, "rb") as f:
        ca_key = serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())
    return ca_cert, ca_key


def issue_contract_certificate(contract, user) -> dict:
    """
    Issue a digital certificate for contract signing.
    Returns dict with cert_pem, serial_number, fingerprint.
    """
    try:
        ca_cert, ca_key = load_ca()
    except Exception:
        # Fallback: generate self-signed for dev
        return _self_signed_fallback(contract, user)

    # Generate key pair for this certificate
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )

    serial = int(secrets.token_hex(16), 16)
    now    = datetime.utcnow()

    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME,             "RW"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME,        "Contract Management System"),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Contracts"),
        x509.NameAttribute(NameOID.COMMON_NAME,              f"CONTRACT-{contract.ref_number}"),
        x509.NameAttribute(NameOID.EMAIL_ADDRESS,            user.email),
    ])

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(private_key.public_key())
        .serial_number(serial)
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=365))
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None), critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([
                ExtendedKeyUsageOID.CODE_SIGNING,
                x509.ObjectIdentifier("1.3.6.1.5.5.7.3.8"),  # time stamping
            ]), critical=False,
        )
        .add_extension(
            x509.SubjectAlternativeName([
                x509.RFC822Name(user.email),
                x509.DNSName(f"contract-{contract.ref_number}.cms.company.com"),
            ]), critical=False,
        )
        .sign(ca_key, hashes.SHA256(), default_backend())
    )

    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
    fp       = cert.fingerprint(hashes.SHA256()).hex()

    return {
        "cert_pem":      cert_pem,
        "serial_number": hex(serial),
        "fingerprint":   fp,
        "subject_dn":    subject.rfc4514_string(),
        "issuer_dn":     ca_cert.subject.rfc4514_string(),
        "valid_from":    now,
        "valid_until":   now + timedelta(days=365),
    }


def verify_certificate(cert_pem: str) -> dict:
    """Verify a PEM certificate against the CA."""
    try:
        ca_cert, _ = load_ca()
        cert = x509.load_pem_x509_certificate(cert_pem.encode(), default_backend())
        # Verify signature
        ca_cert.public_key().verify(
            cert.signature,
            cert.tbs_certificate_bytes,
            cert.signature_hash_algorithm,
        )
        now = datetime.utcnow()
        valid = cert.not_valid_before_utc.replace(tzinfo=None) <= now <= cert.not_valid_after_utc.replace(tzinfo=None)
        return {
            "valid":       valid,
            "subject":     cert.subject.rfc4514_string(),
            "issuer":      cert.issuer.rfc4514_string(),
            "expires":     cert.not_valid_after_utc.isoformat(),
            "serial":      hex(cert.serial_number),
            "fingerprint": cert.fingerprint(hashes.SHA256()).hex(),
        }
    except Exception as e:
        return {"valid": False, "error": str(e)}


def sign_document(document_bytes: bytes, cert_pem: str, private_key_pem: str) -> str:
    """Create a detached digital signature for a document."""
    from cryptography.hazmat.primitives.asymmetric import padding
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode(), password=None, backend=default_backend()
    )
    signature = private_key.sign(document_bytes, padding.PKCS1v15(), hashes.SHA256())
    return signature.hex()


def _self_signed_fallback(contract, user) -> dict:
    """Generate a self-signed cert for development when CA is not available."""
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )
    serial = int(secrets.token_hex(16), 16)
    now    = datetime.utcnow()
    name   = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, f"CONTRACT-{contract.ref_number}"),
        x509.NameAttribute(NameOID.EMAIL_ADDRESS, user.email),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name).issuer_name(name)
        .public_key(private_key.public_key())
        .serial_number(serial)
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=365))
        .sign(private_key, hashes.SHA256(), default_backend())
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
    return {
        "cert_pem":      cert_pem,
        "serial_number": hex(serial),
        "fingerprint":   cert.fingerprint(hashes.SHA256()).hex(),
        "subject_dn":    name.rfc4514_string(),
        "issuer_dn":     name.rfc4514_string(),
        "valid_from":    now,
        "valid_until":   now + timedelta(days=365),
    }
