"""Network, archive and offline bootstrap tests. All payloads are synthetic."""
from __future__ import annotations
import hashlib
import http.server
import json
import socket
import ssl
import subprocess
import threading
import urllib.error
import zipfile
from pathlib import Path
import pytest
import fusion_downloads as dl
import fusion_network as net
from fusion_util import FusionError, atomic_json, sha256
from conftest import pe_bytes


def archive(path, files):
    with zipfile.ZipFile(path,'w') as z:
        for name, data in files.items():z.writestr(name,data)
    return path


@pytest.fixture
def server(tmp_path):
    cert=tmp_path/'test-ca.pem';key=tmp_path/'test-key.pem'
    subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1',
      '-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost','-keyout',str(key),'-out',str(cert)],
      check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body=b'test payload, not a graphics binary'
            self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def log_message(self,*args):pass
    httpd=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(cert,key)
    httpd.socket=context.wrap_socket(httpd.socket,server_side=True)
    thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
    yield cert,httpd.server_port
    httpd.shutdown();httpd.server_close();thread.join(timeout=3)


def local_download_test(monkeypatch,cert=None):
    original=net.tls_context
    if cert:monkeypatch.setattr(dl,'tls_context',lambda:original([cert]))
    # Only the test harness permits localhost/ephemeral ports, production is unchanged.
    monkeypatch.setattr(dl,'checked_url',lambda url:url)
    monkeypatch.setattr(dl.time,'sleep',lambda *_:None)


def test_certificates_and_hostname_verification_are_required():
    context,info=net.tls_context()
    assert context.verify_mode==ssl.CERT_REQUIRED and context.check_hostname
    assert context.minimum_version>=ssl.TLSVersion.TLSv1_2
    assert info['ca_count']>100
    assert str(net.BUNDLED_CA) in info['sources']


def test_mozilla_fallback_when_embedded_python_system_paths_are_missing(monkeypatch):
    monkeypatch.setattr(ssl.SSLContext,'load_default_certs',lambda *_:None)
    monkeypatch.setattr(net,'SYSTEM_CA_FILES',())
    for key in ('SSL_CERT_FILE','REQUESTS_CA_BUNDLE','CURL_CA_BUNDLE'):monkeypatch.delenv(key,raising=False)
    context,info=net.tls_context()
    assert info['sources']==[str(net.BUNDLED_CA)]
    assert info['ca_count']>100 and context.check_hostname


def test_no_trust_store_fails_closed(monkeypatch,tmp_path):
    monkeypatch.setattr(ssl.SSLContext,'load_default_certs',lambda *_:None)
    monkeypatch.setattr(net,'SYSTEM_CA_FILES',())
    monkeypatch.setattr(net,'BUNDLED_CA',tmp_path/'missing.pem')
    for key in ('SSL_CERT_FILE','REQUESTS_CA_BUNDLE','CURL_CA_BUNDLE'):monkeypatch.delenv(key,raising=False)
    with pytest.raises(FusionError,match='verification was not disabled'):net.tls_context()


def test_verified_https_download_uses_supplied_trust(server,monkeypatch,tmp_path):
    cert,port=server;local_download_test(monkeypatch,cert)
    target=tmp_path/'download.bin';data=b'test payload, not a graphics binary'
    result=dl.download(f'https://localhost:{port}/',target,lambda *_:None,hashlib.sha256(data).hexdigest())
    assert target.read_bytes()==data and result['tls_verified'] and result['upstream_digest_verified']
    assert not target.with_suffix('.bin.part').exists()


def test_untrusted_certificate_is_rejected_existing_file_unchanged(server,monkeypatch,tmp_path):
    _,port=server;local_download_test(monkeypatch)
    target=tmp_path/'download.bin';target.write_bytes(b'old valid cache')
    with pytest.raises(FusionError,match='HTTPS certificate validation failed'):
        dl.download(f'https://localhost:{port}/',target,lambda *_:None)
    assert target.read_bytes()==b'old valid cache'
    assert not target.with_suffix('.bin.part').exists()


def test_trusted_certificate_with_wrong_hostname_is_rejected(server,monkeypatch,tmp_path):
    cert,port=server;local_download_test(monkeypatch,cert)
    with pytest.raises(FusionError,match='HTTPS certificate validation failed'):
        dl.download(f'https://127.0.0.1:{port}/',tmp_path/'out',lambda *_:None)


def test_https_bad_digest_preserves_cache_and_cleans_partial(server,monkeypatch,tmp_path):
    cert,port=server;local_download_test(monkeypatch,cert)
    target=tmp_path/'data.bin';target.write_bytes(b'old cache')
    with pytest.raises(FusionError,match='SHA-256 verification failed'):
        dl.download(f'https://localhost:{port}/',target,lambda *_:None,'0'*64)
    assert target.read_bytes()==b'old cache'
    assert not target.with_suffix('.bin.part').exists()


@pytest.mark.parametrize('url',['http://github.com/x','https://evil.example/x','https://github.com:444/x','https://user:pass@github.com/x'])
def test_unapproved_sources_and_https_downgrades_rejected(url):
    with pytest.raises(FusionError):dl.checked_url(url)
    with pytest.raises(FusionError):dl.SafeRedirect().redirect_request(None,None,302,'',{},url)


def test_offline_bootstrap_real_archives_not_network(tmp_path,monkeypatch):
    bundle=tmp_path/'bundle';bundle.mkdir();entries={}
    files={
      'lsfg':{'lib/liblsfg-vk.so':b'\x7fELF\x02'+b'\0'*80,'share/lsfg.json':json.dumps({'layer':{'name':'VK_LAYER_LSFGVK','library_path':'liblsfg-vk.so'}})},
      'opti':{'OptiScaler.dll':pe_bytes(),'OptiScaler.ini':'[Upscalers]\nDx12Upscaler=auto\n'},
      'reshade':{'ReShade64.dll':pe_bytes(),'ReShade32.dll':pe_bytes(32)},
    }
    for name in ('standard','sweetfx','fxshaders'):
        files[name]={'repo/Shaders/Test.fx' if name!='standard' else 'repo/Shaders/ReShade.fxh':'// fixture only, not a usable effect'}
    for name,contents in files.items():
        file=archive(bundle/f'{name}.zip',contents)
        entries[name]={'archive':file.name,'sha256':sha256(file),'version':'2.0.0' if name=='lsfg' else 'test',
          'repository':'example/fixture','commit':'f'*40}
    atomic_json(bundle/'manifest.json',{'components':entries})
    packages=dl.Packages(tmp_path/'data',bundle)
    monkeypatch.setattr(dl,'download',lambda *_,**__:pytest.fail('Offline initialization attempted a network request'))
    result=packages.seed_bundled(lambda *_:None)
    assert result['complete'] and not result['missing'] and not result['errors']
    status=packages.status();assert all(status[k]['source']=='bundle' for k in ('lsfg','opti','reshade'))
    assert len(status['shaders'])==3
    # Existing versions always win over a bundled baseline, even after a plugin restart.
    status['lsfg']['version']='2.0.99';atomic_json(packages.root/'packages.json',status)
    assert dl.Packages(packages.root,bundle).seed_bundled(lambda *_:None)['complete']
    assert packages.status()['lsfg']['version']=='2.0.99'


@pytest.mark.parametrize('entry',[{'archive':'../escape.zip','sha256':'0'*64}, {'archive':'missing.zip','sha256':'0'*64},None,{}])
def test_bad_offline_entry_does_not_crash_state_or_change_cache(tmp_path,entry):
    bundle=tmp_path/'bundle';bundle.mkdir();atomic_json(bundle/'manifest.json',{'components':{'opti':entry}})
    packages=dl.Packages(tmp_path/'data',bundle)
    result=packages.seed_bundled(lambda *_:None)
    assert not result['complete'] and result['errors']
    assert packages.status()=={}


@pytest.mark.parametrize('manifest',[[],{'components':[]},'not a manifest'])
def test_malformed_bundle_manifest_does_not_break_plugin(tmp_path,manifest):
    bundle=tmp_path/'bundle';bundle.mkdir();atomic_json(bundle/'manifest.json',manifest)
    result=dl.Packages(tmp_path/'data',bundle).seed_bundled(lambda *_:None)
    assert not result['complete'] and result['errors']


def test_tampered_offline_archive_is_not_loaded(tmp_path):
    bundle=tmp_path/'bundle';bundle.mkdir();(bundle/'opti.zip').write_bytes(b'tampered')
    atomic_json(bundle/'manifest.json',{'components':{'opti':{'archive':'opti.zip','version':'test','sha256':'0'*64}}})
    packages=dl.Packages(tmp_path/'data',bundle);result=packages.seed_bundled(lambda *_:None)
    assert not result['complete'] and 'SHA-256' in str(result['errors']) and packages.status()=={}


def test_broken_updated_archive_preserves_existing_package(tmp_path):
    packages=dl.Packages(tmp_path/'data');old=packages.packages/'old';old.mkdir()
    atomic_json(packages.root/'packages.json',{'opti':{'version':'old','path':str(old)}})
    file=archive(tmp_path/'new.zip',{'not-a-dll.txt':'invalid upstream response'})
    with pytest.raises(FusionError,match='OptiScaler.dll'):
        packages.install_archive('opti','test',file,{'sha256':sha256(file)},lambda *_:None)
    assert packages.status()['opti']['version']=='old' and old.exists()
    assert not list(packages.packages.glob('.package-*'))


@pytest.mark.parametrize('filename',['../escape','/absolute','Z:/drive','safe/../../escape'])
def test_archive_path_traversal_rejected(tmp_path,filename):
    file=archive(tmp_path/'evil.zip',{filename:'unsafe'})
    with pytest.raises(FusionError):dl.extract(file,tmp_path/'out')


def test_lsfg_update_resolves_stable_2x_only(tmp_path,monkeypatch):
    def download(url,dest,*a,**k):
        dest.write_text('lsfg-vk-2.0.0.tar.xz lsfg-vk-2.0.2.tar.xz lsfg-vk-2.0.1.tar.xz lsfg-vk-2.0.99-rc1.tar.xz lsfg-vk-2.0.99.r1.g123.tar.xz lsfg-vk-3.0.0.tar.xz')
    monkeypatch.setattr(dl,'download',download)
    packages=dl.Packages(tmp_path/'data')
    assert packages.resolve('lsfg',lambda *_:None)['version']=='2.0.0'
    assert packages.resolve('lsfg',lambda *_:None,latest=True)['version']=='2.0.2'


def test_opti_latest_rejects_prerelease(tmp_path,monkeypatch):
    monkeypatch.setattr(dl,'get_json',lambda *_:{'prerelease':True})
    with pytest.raises(FusionError,match='not stable'):dl.Packages(tmp_path/'data').resolve('opti',lambda *_:None)


def test_api_rate_limit_uses_official_release_page(tmp_path,monkeypatch):
    def api(*_):raise FusionError('github refused: HTTP 403')
    def download(url,dest,*_,**__):
        dest.write_text('<a href="/optiscaler/OptiScaler/releases/download/v0.9.4/Optiscaler_0.9.4-final.7z">file</a>')
        return {'final_url':'https://github.com/optiscaler/OptiScaler/releases/tag/v0.9.4'}
    monkeypatch.setattr(dl,'get_json',api);monkeypatch.setattr(dl,'download',download)
    result=dl.Packages(tmp_path/'data').resolve('opti',lambda *_:None)
    assert result['version']=='v0.9.4' and result['url'].endswith('.7z')
    assert result['expected'] is None


def test_reshade_resolution_excludes_addon_installer(tmp_path,monkeypatch):
    def download(url,dest,*_,**__):dest.write_text('/downloads/ReShade_Setup_6.8.0.exe /downloads/ReShade_Setup_99.0.0_Addon.exe /downloads/ReShade_Setup_6.7.0.exe')
    monkeypatch.setattr(dl,'download',download)
    result=dl.Packages(tmp_path/'data').resolve('reshade',lambda *_:None)
    assert result['version']=='6.8.0' and result['url'].endswith('6.8.0.exe')
