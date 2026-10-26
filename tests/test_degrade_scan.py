def test_higher_strength_damages_more() -> None:
    from PIL import Image, ImageChops

    from smart_extractor.degrade_scan import degrade

    page = Image.new("L", (200, 200), 255)
    mild, harsh = degrade(page, 1, 1.0), degrade(page, 1, 3.0)
    assert mild.size == harsh.size
    assert ImageChops.difference(mild, harsh).getbbox() is not None
