"""Verified TLS in Decky's embedded Python as well as SteamOS's system Python.

The interpreter's compiled-in OpenSSL path is not necessarily SteamOS's CA path.
Load the platform stores explicitly and a shipped Mozilla CA fallback. Never turn
certificate/hostname verification off, even when an update fails.
"""
from __future__ import annotations
import os
from pathlib import Path
import ssl
from fusion_util import FusionError

SYSTEM_CA_FILES = (
    '/etc/ssl/certs/ca-certificates.crt',
    '/etc/ssl/cert.pem',
    '/etc/ca-certificates/extracted/tls-ca-bundle.pem',
    '/etc/pki/tls/certs/ca-bundle.crt',
    '/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem',
)
BUNDLED_CA = Path(__file__).resolve().parents[1] / 'certs' / 'cacert.pem'


def tls_context(extra_cafiles=()) -> tuple[ssl.SSLContext, dict]:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    loaded, warnings = [], []
    try:
        context.load_default_certs(ssl.Purpose.SERVER_AUTH)
        if context.cert_store_stats()['x509_ca']:
            loaded.append('OpenSSL default trust store')
    except (OSError, ssl.SSLError) as error:
        warnings.append(f'OpenSSL default store: {error}')
    candidates = [os.environ.get(name, '') for name in ('SSL_CERT_FILE', 'REQUESTS_CA_BUNDLE', 'CURL_CA_BUNDLE')]
    candidates += list(SYSTEM_CA_FILES) + [str(BUNDLED_CA)] + [str(p) for p in extra_cafiles]
    seen = set()
    for value in candidates:
        if not value:
            continue
        path = Path(value).expanduser()
        try:
            real = str(path.resolve())
            if real in seen or not path.is_file():
                continue
            seen.add(real)
            context.load_verify_locations(cafile=str(path))
            loaded.append(str(path))
        except (OSError, ssl.SSLError) as error:
            warnings.append(f'{path}: {error}')
    if not context.cert_store_stats()['x509_ca']:
        raise FusionError('No trusted certificate authorities are available. Reinstall the complete Deck Fusion ZIP (including certs/cacert.pem) or repair the SteamOS CA store. HTTPS verification was not disabled.')
    return context, {
        'certificate_verification': True,
        'hostname_verification': True,
        'minimum_tls': '1.2',
        'ca_count': context.cert_store_stats()['x509_ca'],
        'sources': loaded,
        'warnings': warnings,
        'openssl': ssl.OPENSSL_VERSION,
    }


def certificate_error(error: BaseException) -> bool:
    reason = getattr(error, 'reason', error)
    return isinstance(reason, ssl.SSLCertVerificationError) or 'CERTIFICATE_VERIFY_FAILED' in str(reason)
