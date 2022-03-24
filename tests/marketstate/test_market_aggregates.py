def test_oi_is_zero_when_no_positions(market_state, feed):
    actual_oi_long, actual_oi_short = market_state.oi(feed)
    assert actual_oi_long == 0
    assert actual_oi_short == 0
