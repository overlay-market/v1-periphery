def test_market_state(state, market, feed, ovl, alice, bob):
    # alice build params
    input_collateral_alice = 20000000000000000000  # 20
    input_leverage_alice = 1000000000000000000  # 1
    input_is_long_alice = True
    input_price_limit_alice = 2**256-1

    # bob build params
    input_collateral_bob = 10000000000000000000  # 10
    input_leverage_bob = 1000000000000000000  # 1
    input_is_long_bob = False
    input_price_limit_bob = 0

    # approve max for both
    ovl.approve(market, 2**256-1, {"from": alice})
    ovl.approve(market, 2**256-1, {"from": bob})

    # build position for alice
    market.build(input_collateral_alice, input_leverage_alice,
                 input_is_long_alice, input_price_limit_alice, {"from": alice})

    # build position for bob
    market.build(input_collateral_bob, input_leverage_bob,
                 input_is_long_bob, input_price_limit_bob, {"from": bob})

    # query all the views from OverlayV1PriceState, OverlayV1OIState
    # NOTE: tests in test_price.py, test_volume.py and test_oi.py
    bid = state.bid(market, 0)
    ask = state.ask(market, 0)
    mid = state.mid(market)
    volume_bid = state.volumeBid(market, 0)
    volume_ask = state.volumeAsk(market, 0)
    oi_long, oi_short = state.ois(market)
    cap_oi = state.capOi(market)
    circuit_level = state.circuitBreakerLevel(market)
    funding_rate = state.fundingRate(market)

    expect = (bid, ask, mid, volume_bid, volume_ask, oi_long, oi_short,
              cap_oi, circuit_level, funding_rate)
    actual = state.marketState(market)
    assert expect == actual
