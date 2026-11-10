"""Opt-in localhost ComfyUI adapter; never starts, downloads, or connects to cloud models."""
from __future__ import annotations

import copy
import http.client
import io
import json
import secrets
from pathlib import Path
from urllib.parse import urlencode

from PIL import Image

COMFY_HOST = "127.0.0.1"
COMFY_PORT = 8188
MAX_ASSET_BYTES = 120 * 1024 * 1024
MAX_WORKFLOW_BYTES = 1024 * 1024


class ComfyUnavailable(RuntimeError):
    pass


class ComfyInvalid(RuntimeError):
    pass


class ComfyClient:
    """Fixed loopback target prevents user-controlled URL/SSRF and cloud surprises."""
    def __init__(self, port: int = COMFY_PORT):
        if not 1 <= port <= 65535:
            raise ValueError("Port invalid")
        self.port = port

    def request(self, method: str, path: str, *, body: bytes | None = None,
                content_type: str | None = None, max_bytes: int = 1024 * 1024) -> bytes:
        if not path.startswith('/') or '://' in path or '\\' in path:
            raise ComfyInvalid("ComfyUI: cale nevalidă")
        conn = http.client.HTTPConnection(COMFY_HOST, self.port, timeout=6 if method == 'GET' else 20)
        try:
            headers = {'Accept': 'application/json'}
            if content_type:
                headers['Content-Type'] = content_type
            conn.request(method, path, body=body, headers=headers)
            response = conn.getresponse()
            if response.status not in (200, 201):
                detail = response.read(8192).decode('utf-8', errors='replace')
                raise ComfyInvalid(f"ComfyUI a răspuns HTTP {response.status}: {detail[:400]}")
            length = response.getheader('Content-Length')
            if length and int(length) > max_bytes:
                raise ComfyInvalid("Fișierul generat este prea mare")
            data = response.read(max_bytes + 1)
            if len(data) > max_bytes:
                raise ComfyInvalid("Răspunsul ComfyUI este prea mare")
            return data
        except (OSError, TimeoutError, http.client.HTTPException) as ex:
            raise ComfyUnavailable("ComfyUI local nu răspunde pe 127.0.0.1:8188") from ex
        finally:
            conn.close()

    def json(self, method: str, path: str, payload=None):
        try:
            data = self.request(method, path, body=json.dumps(payload).encode() if payload is not None else None,
                                content_type='application/json' if payload is not None else None)
            return json.loads(data)
        except (ValueError, UnicodeDecodeError) as ex:
            raise ComfyInvalid("ComfyUI a trimis JSON invalid") from ex

    def status(self):
        details = self.json('GET', '/system_stats')
        return {'connected': True, 'endpoint': f'http://{COMFY_HOST}:{self.port}',
                'devices': [str(x.get('name', 'dispozitiv')) for x in details.get('devices', [])]}

    def checkpoints(self):
        names = self.json('GET', '/models/checkpoints')
        if not isinstance(names, list):
            raise ComfyInvalid("Lista checkpoint-urilor nu este validă")
        return [x for x in names if isinstance(x, str) and len(x) <= 200][:100]

    def upload_image(self, filename: str, data: bytes) -> str:
        if not data or len(data) > 50 * 1024 * 1024:
            raise ComfyInvalid("Fotografia sursă este prea mare")
        # We do not allow callers to pick a ComfyUI filesystem path.
        filename = 'vega_src_' + secrets.token_hex(12) + ('.png' if data.startswith(b'\x89PNG') else '.jpg')
        boundary = '----vega' + secrets.token_hex(14)
        fields = (f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{filename}"\r\n'
                  f'Content-Type: image/png\r\n\r\n').encode()
        fields = fields.replace(b'image/png', b'image/jpeg') if filename.endswith('.jpg') else fields
        content = fields + data + f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="type"\r\n\r\ninput\r\n--{boundary}--\r\n'.encode()
        result = json.loads(self.request('POST', '/upload/image', body=content,
                       content_type=f'multipart/form-data; boundary={boundary}', max_bytes=65536))
        name = result.get('name', '')
        if not isinstance(name, str) or not name or '/' in name or '\\' in name:
            raise ComfyInvalid("ComfyUI nu a confirmat imaginea")
        return name

    def enqueue(self, workflow):
        data = self.json('POST', '/prompt', {'prompt': workflow, 'client_id': 'vega-' + secrets.token_hex(8)})
        pid = data.get('prompt_id')
        if not isinstance(pid, str) or len(pid) > 128 or not pid:
            raise ComfyInvalid(f"ComfyUI nu a acceptat workflow-ul: {str(data.get('error', data))[:350]}")
        return pid

    def history(self, prompt_id):
        if not prompt_id or any(c not in '0123456789abcdef-' for c in prompt_id.lower()):
            raise ComfyInvalid("ID generare invalid")
        return self.json('GET', '/history/' + prompt_id)

    def download_output(self, meta):
        name = meta.get('filename') if isinstance(meta, dict) else None
        subfolder = meta.get('subfolder', '') if isinstance(meta, dict) else ''
        typ = meta.get('type', 'output') if isinstance(meta, dict) else 'output'
        if not isinstance(name, str) or not name or len(name) > 255 or '/' in name or '\\' in name or '..' in name:
            raise ComfyInvalid("Nume rezultat invalid")
        if not isinstance(subfolder, str) or '..' in subfolder or '\\' in subfolder or subfolder.startswith('/'):
            raise ComfyInvalid("Subfolder rezultat invalid")
        if typ != 'output':
            raise ComfyInvalid("Sunt acceptate numai rezultate finale ComfyUI")
        path = '/view?' + urlencode({'filename': name, 'subfolder': subfolder, 'type': 'output'})
        return self.request('GET', path, max_bytes=MAX_ASSET_BYTES)


def photo_workflow(checkpoint: str, prompt: str, negative: str, width: int, height: int):
    if not 256 <= width <= 1024 or not 256 <= height <= 1024 or width % 64 or height % 64:
        raise ComfyInvalid('Rezoluția trebuie să fie între 256 și 1024 și multiplu de 64')
    # This is the standard ComfyUI API graph, not a remote API request.
    return {
        '1': {'class_type':'CheckpointLoaderSimple','inputs':{'ckpt_name':checkpoint}},
        '2': {'class_type':'CLIPTextEncode','inputs':{'text':prompt,'clip':['1',1]}},
        '3': {'class_type':'CLIPTextEncode','inputs':{'text':negative,'clip':['1',1]}},
        '4': {'class_type':'EmptyLatentImage','inputs':{'width':width,'height':height,'batch_size':1}},
        '5': {'class_type':'KSampler','inputs':{'seed':secrets.randbelow(2**53),'steps':16,'cfg':6.5,
             'sampler_name':'euler','scheduler':'normal','denoise':1.0,'model':['1',0],
             'positive':['2',0],'negative':['3',0],'latent_image':['4',0]}},
        '6': {'class_type':'VAEDecode','inputs':{'samples':['5',0],'vae':['1',2]}},
        '7': {'class_type':'SaveImage','inputs':{'filename_prefix':'VEGA_AI','images':['6',0]}}
    }


def validate_workflow(data: bytes):
    if len(data) > MAX_WORKFLOW_BYTES:
        raise ComfyInvalid('Workflow-ul depășește 1 MB')
    try:
        result = json.loads(data)
    except (ValueError, UnicodeDecodeError) as ex:
        raise ComfyInvalid('Fișier JSON invalid') from ex
    if not isinstance(result, dict) or not 2 <= len(result) <= 250:
        raise ComfyInvalid('Este necesar un workflow ComfyUI în format API, cu noduri class_type/inputs')
    for key, node in result.items():
        if not isinstance(key, str) or not key.isdecimal() or not isinstance(node, dict) or \
                not isinstance(node.get('class_type'), str) or not isinstance(node.get('inputs'), dict):
            raise ComfyInvalid('Workflow incorect; folosește Export/API din ComfyUI')
    return result


def prepare_video_workflow(template: dict, *, prompt: str, negative: str,
                           uploaded_image: str | None = None):
    graph = copy.deepcopy(template)
    changed_prompt = 0
    changed_image = 0
    for node in graph.values():
        inputs = node['inputs']
        for key, value in list(inputs.items()):
            if not isinstance(value, str):
                continue
            if '__VEGA_PROMPT__' in value:
                inputs[key] = value.replace('__VEGA_PROMPT__', prompt); changed_prompt += 1
            if '__VEGA_NEGATIVE__' in value:
                inputs[key] = value.replace('__VEGA_NEGATIVE__', negative)
            if uploaded_image and '__VEGA_IMAGE__' in value:
                inputs[key] = uploaded_image; changed_image += 1
        if node['class_type'] == 'CLIPTextEncode' and changed_prompt == 0 and isinstance(inputs.get('text'), str):
            inputs['text'] = prompt
            changed_prompt += 1
        if uploaded_image and node['class_type'] == 'LoadImage' and changed_image == 0:
            inputs['image'] = uploaded_image
            changed_image += 1
    if not changed_prompt:
        raise ComfyInvalid('Workflow-ul video trebuie să conțină CLIPTextEncode sau __VEGA_PROMPT__')
    if uploaded_image and not changed_image:
        raise ComfyInvalid('Workflow-ul video nu are nod LoadImage sau __VEGA_IMAGE__')
    return graph


def select_result(history_data: dict, prompt_id: str, mode: str):
    result = history_data.get(prompt_id)
    if result is None:
        return 'queued', None
    status = result.get('status', {})
    if status.get('status_str') in ('error', 'failed') or status.get('completed') is False:
        return 'failed', None
    outputs = result.get('outputs', {})
    items = []
    for node in outputs.values():
        for category in ('images', 'videos', 'gifs'):
            values = node.get(category, [])
            if isinstance(values, list):
                items.extend(values)
    wanted = {'.png', '.jpg', '.jpeg', '.webp'} if mode == 'image' else {'.mp4', '.webm'}
    for item in items:
        if isinstance(item, dict) and item.get('type', 'output') == 'output' and \
                Path(str(item.get('filename', ''))).suffix.lower() in wanted:
            return 'complete', item
    if status.get('completed') is True:
        return 'failed', None
    return 'queued', None


def validate_generated(data: bytes, mode: str, suffix: str):
    if not data or len(data) > MAX_ASSET_BYTES:
        raise ComfyInvalid('Rezultatul AI este gol sau prea mare')
    if mode == 'image':
        try:
            with Image.open(io.BytesIO(data)) as im:
                if im.format not in {'PNG','JPEG','WEBP'} or im.width*im.height > 28_000_000:
                    raise ComfyInvalid('Imaginea AI are formatul sau rezoluția invalidă')
                im.verify()
        except (OSError, ValueError) as ex:
            raise ComfyInvalid('Imagine generată invalidă') from ex
    elif suffix == '.mp4' and (len(data) < 12 or data[4:8] != b'ftyp'):
        raise ComfyInvalid('MP4 generat invalid')
    elif suffix == '.webm' and not data.startswith(b'\x1a\x45\xdf\xa3'):
        raise ComfyInvalid('WebM generat invalid')
