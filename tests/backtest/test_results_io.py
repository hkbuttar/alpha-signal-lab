from backtest import results_io


def test_load_sample_metrics_returns_flat_full_period_dict():
    metrics = results_io.load_sample_metrics()

    assert metrics is not None
    assert all(not isinstance(v, dict) for v in metrics.values())
    assert "cagr" in metrics
    assert "sharpe_ratio" in metrics


def test_load_sample_metrics_matches_a_real_run_shape():
    runs = results_io.list_runs()
    assert runs, "expected at least one committed run to compare against"

    _, run_metrics = results_io.load_run(runs[0])
    sample_metrics = results_io.load_sample_metrics()

    assert set(sample_metrics.keys()) == set(run_metrics.keys())
