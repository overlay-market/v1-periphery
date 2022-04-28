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
    bid = state.bid(feed, 0)
    ask = state.ask(feed, 0)
    mid = state.mid(feed)
    volume_bid = state.volumeBid(feed, 0)
    volume_ask = state.volumeAsk(feed, 0)
    oi_long, oi_short = state.ois(feed)
    cap_oi = state.capOi(feed)
    circuit_level = state.circuitBreakerLevel(feed)
    funding_rate = state.fundingRate(feed)

    expect = (bid, ask, mid, volume_bid, volume_ask, oi_long, oi_short,
              cap_oi, circuit_level, funding_rate)
    actual = state.marketState(feed)
    assert expect == actual
