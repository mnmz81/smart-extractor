from smart_extractor.calibrate import threshold_curve


def test_curve_shows_share_and_accuracy_at_each_threshold() -> None:
    points = [(1.0, True), (0.8, True), (0.5, False), (0.0, False)]
    assert threshold_curve(points) == [
        (0.0, 1.0, 0.5),  # approve everything: 2 of 4 correct
        (0.5, 0.75, 2 / 3),
        (0.8, 0.5, 1.0),
        (1.0, 0.25, 1.0),
    ]
