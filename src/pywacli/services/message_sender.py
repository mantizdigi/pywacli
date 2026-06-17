import json
import socket

_node_process = None


def set_node_process(proc):
    global _node_process
    _node_process = proc


def send_message(phone, text, uri=None, jid=None):
    jid_value = jid or f"{phone}@s.whatsapp.net"
    payload = {"event": "send.message", "data": {"jid": jid_value, "text": text}}

    # Same process as the running session (e.g. CLI `connect`): write straight
    # to the node bridge's stdin.
    if _node_process is not None:
        _node_process.stdin.write(json.dumps(payload) + "\n")
        _node_process.stdin.flush()
        return

    # Separate process (the Send terminal): hand the message to the running
    # Connect session over its local command socket. No second WhatsApp socket.
    _send_via_socket(payload)


def send_message_to_group(group_id, text, uri=None):
    return send_message("", text, uri=uri, jid=group_id)


def _send_via_socket(payload):
    from pywacli.cli.config_manager import get_send_host, get_send_port

    host, port = get_send_host(), get_send_port()
    try:
        with socket.create_connection((host, port), timeout=10) as sock:
            sock.sendall((json.dumps(payload) + "\n").encode("utf-8"))
            sock.settimeout(20)
            resp = b""
            while b"\n" not in resp:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                resp += chunk
    except (ConnectionRefusedError, OSError) as e:
        raise RuntimeError(
            f"Can't reach the WhatsApp service on {host}:{port}. "
            f"Start Connect (option 4) in another terminal first."
        ) from e

    line = resp.split(b"\n", 1)[0].decode("utf-8", "replace").strip()
    if not line:
        raise RuntimeError("No response from the WhatsApp service.")

    data = json.loads(line)
    if data.get("event") == "error":
        raise RuntimeError(data.get("data", {}).get("message", "Send failed"))
    # event == "message.sent" -> delivered to the bridge
