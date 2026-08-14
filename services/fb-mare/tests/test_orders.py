from mare_service.orders import build_order
from mare_service.strategy import MareSignal, Screen


def test_order_has_shared_contract_shape():
    screen = Screen("bull", 0.9, 1.0, "test")
    signal = MareSignal("BTC/USDT", "LONG", 0.8, True, "ACCEPTED", screen, screen, Screen("up", 0.8, 0.01, "test"), 100.0, 1.0)
    order = build_order(signal, 10)
    assert order["block_id"] == "mare"
    assert order["strategy"] == "elder_triple_screen"
    assert order["direction"] == "LONG"
    assert order["exit"]["sl_price"] < order["exit"]["tp_price"]
    for key in ("order_id", "client_order_id", "entry", "quantity", "notional_usdt", "exit", "execution"):
        assert key in order
