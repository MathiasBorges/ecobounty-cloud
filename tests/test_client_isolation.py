"""Isolamento de estado entre dispositivos (cid) no servidor auxiliar em tempo real."""
from app.services import storage_service as ss


def _reset():
    ss._PENDING_ACTIONS.clear()
    ss._LATEST_PHOTOS.clear()
    ss._PHOTO_LISTENERS.clear()
    ss._LOCATION_LISTENERS.clear()
    ss._BOUNTY_LISTENERS.clear()
    ss._GOOGLE_AUTH_RESULTS.clear()


def test_acao_pendente_nao_vaza_entre_dispositivos():
    _reset()
    ss.set_pending_action("open_camera", {"mode": "denuncia"}, cid="A")
    assert ss.pop_pending_action(cid="B") == (None, {})
    assert ss.pop_pending_action(cid="A") == ("open_camera", {"mode": "denuncia"})
    assert ss.pop_pending_action(cid="A") == (None, {})


def test_foto_chega_apenas_ao_dispositivo_que_fotografou():
    _reset()
    recebidas = {"A": [], "B": []}
    ss.register_photo_listener(lambda p: recebidas["A"].append(p), cid="A")
    ss.register_photo_listener(lambda p: recebidas["B"].append(p), cid="B")
    ss.set_latest_captured_photo("/uploads/foto_a.jpg", cid="A")
    assert recebidas["A"] == ["/uploads/foto_a.jpg"]
    assert recebidas["B"] == []
    assert ss.get_latest_captured_photo(cid="A") == "/uploads/foto_a.jpg"
    assert ss.get_latest_captured_photo(cid="B") is None


def test_gps_e_selecao_de_missao_isolados():
    _reset()
    gps = {"A": [], "B": []}
    sel = {"A": [], "B": []}
    ss.register_location_listener(lambda la, lo: gps["A"].append((la, lo)), cid="A")
    ss.register_location_listener(lambda la, lo: gps["B"].append((la, lo)), cid="B")
    ss.register_bounty_listener(lambda i: sel["A"].append(i), cid="A")
    ss.register_bounty_listener(lambda i: sel["B"].append(i), cid="B")
    ss.notify_location_update(-9.66, -35.73, cid="B")
    ss.notify_bounty_selected(7, cid="A")
    assert gps == {"A": [], "B": [(-9.66, -35.73)]}
    assert sel == {"A": [7], "B": []}


def test_login_google_isolado_por_dispositivo():
    _reset()
    ss.set_google_auth_result({"status": "success", "email": "a@x.com"}, cid="A")
    assert ss.pop_google_auth_result(cid="B") is None
    assert ss.pop_google_auth_result(cid="A")["email"] == "a@x.com"
    assert ss.pop_google_auth_result(cid="A") is None


def test_modo_legado_sem_cid_continua_funcionando():
    _reset()
    ss.set_pending_action("request_gps")
    assert ss.pop_pending_action() == ("request_gps", {})
    visto = []
    ss.register_photo_listener(visto.append)
    ss.set_latest_captured_photo("/uploads/x.jpg")
    assert visto == ["/uploads/x.jpg"]


def test_unregister_remove_ouvinte():
    _reset()
    visto = []
    cb = visto.append
    ss.register_photo_listener(cb, cid="A")
    ss.unregister_photo_listener(cb)
    ss.set_latest_captured_photo("/uploads/y.jpg", cid="A")
    assert visto == []

