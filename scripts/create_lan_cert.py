"""Create a private-network-only VEGA TLS root+server cert; private CA signing key is not stored."""
from __future__ import annotations

import hashlib
import ipaddress
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get('VEGA_DATA_DIR', ROOT / 'local_data')).resolve()
DIR = DATA / 'lan_certs'


def private_ipv4(raw: str) -> str:
    ip = ipaddress.ip_address(raw.strip())
    if ip.version != 4 or not ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_unspecified:
        raise ValueError('Alege adresa IPv4 privată a PC-ului, ex. 192.168.1.25')
    return str(ip)


def generate(ip: str):
    ip = private_ipv4(ip)
    DIR.mkdir(parents=True, exist_ok=True)
    ca_path = DIR / 'VEGA-CA.cer'
    cert_path = DIR / 'vega-server.crt'
    key_path = DIR / 'vega-server.key'
    if any(p.exists() for p in (ca_path, cert_path, key_path)):
        if not all(p.exists() for p in (ca_path, cert_path, key_path)):
            raise RuntimeError('Certificat LAN incomplet. Salvează backupul și șterge manual folderul lan_certs.')
        cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
        addr = ipaddress.ip_address(ip)
        cert_ips = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.IPAddress)
        if addr not in cert_ips or cert.not_valid_after_utc < datetime.now(timezone.utc) + timedelta(days=2):
            raise RuntimeError('IP-ul s-a schimbat sau certificatul a expirat; șterge manual lan_certs și refă încrederea pe iPhone.')
        return ca_path, cert_path, key_path

    now = datetime.now(timezone.utc)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'VEGA LAN Local CA')])
    ca = (x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name)
          .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
          .not_valid_before(now-timedelta(minutes=10)).not_valid_after(now+timedelta(days=730))
          .add_extension(x509.BasicConstraints(ca=True,path_length=0),critical=True)
          .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()),critical=False)
          .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),critical=False)
          .add_extension(x509.KeyUsage(digital_signature=True,key_encipherment=False,content_commitment=False,
                          data_encipherment=False,key_agreement=False,key_cert_sign=True,crl_sign=True,
                          encipher_only=False,decipher_only=False),critical=True)
          .sign(ca_key,hashes.SHA256()))
    server_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    server_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, f'VEGA-{ip}')])
    leaf = (x509.CertificateBuilder().subject_name(server_name).issuer_name(ca_name)
            .public_key(server_key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now-timedelta(minutes=10)).not_valid_after(now+timedelta(days=365))
            .add_extension(x509.BasicConstraints(ca=False,path_length=None),critical=True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(server_key.public_key()),critical=False)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),critical=False)
            .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address(ip))]),critical=False)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),critical=False)
            .add_extension(x509.KeyUsage(digital_signature=True,key_encipherment=True,content_commitment=False,
                            data_encipherment=False,key_agreement=False,key_cert_sign=False,crl_sign=False,
                            encipher_only=False,decipher_only=False),critical=True)
            .sign(ca_key,hashes.SHA256()))
    ca_path.write_bytes(ca.public_bytes(serialization.Encoding.DER))
    cert_path.write_bytes(leaf.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(server_key.private_bytes(serialization.Encoding.PEM,
                            serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
    try: os.chmod(key_path, 0o600)
    except OSError: pass
    # The CA private key exists only in process memory; no PEM file is written for it.
    return ca_path,cert_path,key_path


def main():
    if len(sys.argv) != 2:
        print('Usage: python scripts/create_lan_cert.py 192.168.x.x',file=sys.stderr)
        return 2
    try:
        ca, cert, key = generate(sys.argv[1])
    except Exception as ex:
        print('Eroare configurare HTTPS:',ex,file=sys.stderr)
        return 1
    print('VEGA HTTPS ready. iPhone URL: https://'+private_ipv4(sys.argv[1])+':8766')
    print('CA CERTIFICATE (AirDrop to iPhone; NEVER send private keys):',ca)
    print('CA SHA256 fingerprint:',hashlib.sha256(ca.read_bytes()).hexdigest())
    print('SERVER certificate:',cert)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
