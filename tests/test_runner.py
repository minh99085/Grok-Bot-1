from loop.runner import goal, run_goal, run_loop


def test_run_goal_stops_on_condition():
    n = {"i": 0}

    def step():
        n["i"] += 1

    ok, iters = run_goal(step, lambda: n["i"] >= 3, max_iterations=100)
    assert ok is True
    assert iters == 3


def test_run_loop_respects_iteration_cap():
    n = {"i": 0}

    @goal(max_iterations=5)
    def tick():
        n["i"] += 1

    iters = run_loop(tick, interval_seconds=0)
    assert iters == 5